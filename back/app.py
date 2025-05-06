"""Flask application for student course management system.

Provides API endpoints for authentication, enrollment, and course management.
"""

import logging

import database
from config import config
from email_utils import send_enrollment_email
from flask import Flask, abort, jsonify, request
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from models import User
from werkzeug.security import (
    check_password_hash,  # For password handling
    generate_password_hash,
)
from flask_cors import CORS


# --- App Setup ---
app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
CORS(app)  # Uncomment if frontend served from different origin

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
# If user is not logged in and tries to access protected route, send 401
# Don't redirect, just fail (frontend handles redirect)
login_manager.login_view = None
login_manager.session_protection = "strong"  # Helps prevent session hijacking


@login_manager.user_loader
def load_user(user_id):
    """Load user from DB based on ID stored in session cookie."""
    user_data = database.find_user_by_id(int(user_id))
    if user_data:
        return User(user_data)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Return 401 Unauthorized error if login is required.

    Returns a 401 error when user isn't logged in.
    """
    return jsonify(message="Authentication required."), 401


# --- API Endpoints ---
@app.route("/api/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify if the service is running.
    Returns a simple JSON response indicating the service status.
    """
    return jsonify({"status": "ok"}), 200


@app.route("/api/login", methods=["POST"])
def login():
    """Handle user login."""
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        abort(400, description="Missing email or password.")  # Bad request

    email = data["email"]
    password = data["password"]

    user_data = database.find_user_by_email(email)

    if user_data and check_password_hash(user_data["password_hash"], password):
        # Password matches
        user = User(user_data)
        login_user(
            user, remember=True
        )  # 'remember=True' keeps user logged in across browser sessions
        logging.info("User %s logged in successfully.", user.email)
        # Return only necessary info, avoid sending hash
        return jsonify(
            message="Login successful",
            user={"id": user.id, "email": user.email, "name": user.name},
        )
    else:
        # Invalid credentials
        logging.warning("Failed login attempt for email: %s", email)
        return jsonify(message="Invalid credentials"), 401


@app.route("/api/logout", methods=["POST"])
@login_required  # Ensures only logged-in users can log out
def logout():
    """Handle user logout."""
    user_email = current_user.email  # Get email before logging out for logging
    logout_user()
    logging.info("User %s logged out successfully.", user_email)
    return jsonify(message="Logout successful")


@app.route("/api/dashboard", methods=["GET"])
@login_required  # Protect this route
def get_dashboard():
    """Retrieve data for the student dashboard."""
    user_id = current_user.id

    enrolled = database.get_enrolled_courses(user_id)
    available = database.get_available_courses(user_id)

    # Prepare student data (avoid sending sensitive info)
    student_info = {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
    }

    return jsonify(
        {"student": student_info, "enrolled": enrolled, "available": available}
    )


@app.route("/api/enroll", methods=["POST"])
@login_required  # Protect this route
def enroll_course():
    """Enrolls the current user in a selected course."""
    data = request.get_json()
    if not data or "courseId" not in data:
        abort(400, description="Missing courseId.")

    try:
        course_id = int(data["courseId"])
    except ValueError:
        abort(400, description="Invalid courseId format.")

    user_id = current_user.id

    # 1. Check if already enrolled
    if database.check_if_enrolled(user_id, course_id):
        logging.warning(
            "User %s attempt to re-enroll in course %s", user_id, course_id
        )
        return (
            jsonify(message="Already enrolled in this course."),
            400,  # Bad request / conflict
        )

    # 2. Attempt enrollment in DB
    success = database.enroll_user_in_course(user_id, course_id)

    if success:
        logging.info(
            "User %s successfully enrolled in course %s", user_id, course_id
        )

        # 3. Send confirmation email (optional - proceed even if email fails)
        course_details = database.get_course_details(course_id)
        course_name = (
            course_details["name"]
            if course_details
            else f"Course ID {course_id}"
        )

        email_sent = send_enrollment_email(
            recipient_email=current_user.email,
            student_name=current_user.name,
            course_name=course_name,
        )
        if not email_sent:
            logging.error(
                "Failed to send enrollment email to %s for course %s, "
                "but enrollment succeeded.",
                current_user.email,
                course_id,
            )
            # Decide if this should be an error response - usually not critical
            # for the enrollment itself

        return jsonify(message="Enrollment successful")
    else:
        logging.error(
            "Database error during enrollment for user %s in course %s",
            user_id,
            course_id,
        )
        return (
            jsonify(message="Enrollment failed due to a server error."),
            500,
        )  # Internal server error


# --- Helper for password hashing (run manually once to add users) ---
# You'd typically have a separate script or admin interface for user creation
@app.route("/create_hash/<password>")
def create_hash(password):
    """Generate a password hash for development/setup purposes.

    Args:
        password (str): The plain text password to hash.

    Returns:
        str: The generated password hash.
    """
    # **NEVER expose this in production** - for dev/setup only
    # Example: Access /create_hash/mypassword123 in browser
    return generate_password_hash(password, method="pbkdf2:sha256")


# --- Run the App ---
if __name__ == "__main__":
    # Use debug=True only for development
    # For production, use a proper WSGI server like Gunicorn:
    # gunicorn -w 4 -b 0.0.0.0:5000 app:app
    # (Listen on all interfaces on port 5000)
    app.run(host="0.0.0.0", port=5001, debug=True)
