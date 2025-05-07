# app.py
import logging
import os
import database  # Vos fonctions DB
from config import config  # Votre config
from email_utils import send_enrollment_email  # Votre utilitaire email
from flask import Flask, abort, jsonify, request
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from models import User  # Votre modèle User
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,  # Utilisé dans create_hash et dans database.py
)
from flask_cors import CORS  # Si vous l'utilisez

# Configuration du logging de base pour l'application Flask
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]",
)

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
CORS(
    app, supports_credentials=True
)  # supports_credentials=True est important pour les sessions avec cookies

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None
login_manager.session_protection = "strong"


@login_manager.user_loader
def load_user(user_id):
    user_data = database.find_user_by_id(int(user_id))
    if user_data:
        return User(user_data)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify(
        message="Authentication required. Please login."
    ), 401  # Message plus clair


# --- API Endpoints ---


@app.route("/api/health", methods=["GET"])  # Endpoint de health check
def health_check():
    return jsonify(status="ok", message="Backend is running"), 200


@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()
    if not all(
        key in data for key in ("name", "email", "password")
    ):  # Manière plus concise de vérifier
        return jsonify(message="Missing name, email, or password."), 400

    name = data["name"].strip()
    email = data["email"].strip().lower()  # Standardiser l'email en minuscules
    password = data["password"]

    if not name or not email or not password:
        return jsonify(
            message="Name, email, and password cannot be empty."
        ), 400

    # Ajouter une validation simple du format de l'email
    # Vous pourriez utiliser une regex plus complexe ou une librairie pour une validation poussée
    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(message="Invalid email format."), 400

    if len(password) < 6:
        return jsonify(
            message="Password must be at least 6 characters long."
        ), 400

    success, message = database.create_user(name, email, password)

    if success:
        return jsonify(message=message), 201
    elif message == "Email already exists.":
        return jsonify(message=message), 409
    else:  # Autres erreurs de DB
        return jsonify(
            message="Could not create user due to a server error."
        ), 500


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify(
            message="Missing email or password."
        ), 400  # Plus explicite qu'abort

    email = data["email"].strip().lower()  # Standardiser l'email
    password = data["password"]

    user_data = database.find_user_by_email(email)

    if user_data and check_password_hash(user_data["password_hash"], password):
        user = User(user_data)
        login_user(user, remember=True)
        app.logger.info(
            f"User {user.email} logged in successfully."
        )  # Utiliser app.logger
        return jsonify(
            message="Login successful",
            user={"id": user.id, "email": user.email, "name": user.name},
        )
    else:
        app.logger.warning(f"Failed login attempt for email: {email}")
        return jsonify(
            message="Invalid email or password."
        ), 401  # Message plus générique


@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    if current_user and hasattr(
        current_user, "email"
    ):  # Vérifier que current_user est bien chargé
        user_email = current_user.email
        logout_user()
        app.logger.info(f"User {user_email} logged out successfully.")
    else:  # Au cas où current_user ne serait pas défini comme attendu
        logout_user()  # Tenter quand même de déconnecter la session
        app.logger.info("User logged out successfully (email not available).")
    return jsonify(message="Logout successful")


@app.route("/api/dashboard", methods=["GET"])
@login_required
def get_dashboard():
    user_id = current_user.id

    enrolled_courses = database.get_enrolled_courses(user_id)
    available_courses = database.get_available_courses(user_id)
    finished_courses = database.get_finished_courses(user_id)

    student_info = {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
    }
    # Log pour débogage
    # app.logger.debug(f"Dashboard data for user {user_id}: Enrolled: {len(enrolled_courses)}, Available: {len(available_courses)}, Finished: {len(finished_courses)}")

    return jsonify(
        {
            "student": student_info,
            "enrolled": enrolled_courses
            if enrolled_courses is not None
            else [],  # Assurer que c'est tjs une liste
            "available": available_courses
            if available_courses is not None
            else [],
            "finished": finished_courses
            if finished_courses is not None
            else [],
        }
    )


@app.route("/api/enroll", methods=["POST"])
@login_required
def enroll_course():
    data = request.get_json()
    if not data or "courseId" not in data:
        return jsonify(message="Missing courseId."), 400

    try:
        course_id = int(data["courseId"])
    except ValueError:
        return jsonify(message="Invalid courseId format."), 400

    user_id = current_user.id

    # 1. Vérifier si déjà activement inscrit
    if database.check_if_enrolled(
        user_id, course_id
    ):  # check_if_enrolled vérifie status='enrolled'
        app.logger.warning(
            f"User {user_id} attempt to re-enroll in active course {course_id}"
        )
        return jsonify(
            message="Already actively enrolled in this course."
        ), 409  # Conflict

    # 2. Tentative d'inscription
    # La fonction enroll_user_in_course devrait gérer le cas où une inscription existe mais avec statut 'finished'
    # ou s'assurer qu'une nouvelle inscription est créée avec statut 'enrolled'.
    # Actuellement, enroll_user_in_course fait un simple INSERT, ce qui échouerait si une contrainte unique (user_id, course_id)
    # existe sur la table enrollments.
    # Si la contrainte unique est (user_id, course_id), il faudrait un UPDATE si l'inscription existe (même 'finished')
    # ou un INSERT si elle n'existe pas.
    #
    # Pour l'instant, avec check_if_enrolled (qui vérifie status='enrolled'), on ne devrait pas arriver ici si déjà 'enrolled'.
    # Si le cours était 'finished', check_if_enrolled retournerait False.
    # Il faudrait donc une logique pour "ré-inscrire" (passer de 'finished' à 'enrolled')
    # ou s'assurer que enroll_user_in_course gère cela.
    #
    # Simplifions : on suppose que enroll_user_in_course insère une nouvelle ligne avec statut 'enrolled'
    # et que le frontend ne propose pas "Enroll" si le cours est 'finished' pour cet utilisateur.
    # Si l'on veut permettre de "recommencer" un cours fini, il faudrait une logique d'UPDATE.
    #
    # Votre `enroll_user_in_course` fait un simple INSERT.
    # S'il y a une contrainte UNIQUE sur (user_id, course_id) dans la DB,
    # et que l'étudiant a déjà une entrée pour ce cours (même 'finished'), l'INSERT échouera.
    # Il faudrait:
    #   1. Vérifier si une entrée (user_id, course_id) existe.
    #   2. Si oui, et status='finished', UPDATE status='enrolled'.
    #   3. Si non, INSERT.
    #
    # Pour l'instant, on s'en tient à votre logique existante qui devrait fonctionner si
    # un utilisateur ne peut pas s'inscrire à un cours qu'il a déjà, quel que soit son statut.
    # (Ce qui est géré par get_available_courses).

    success = database.enroll_user_in_course(user_id, course_id)

    if success:
        app.logger.info(
            f"User {user_id} successfully enrolled in course {course_id}"
        )
        course_details = database.get_course_details(course_id)
        course_name = (
            course_details["name"]
            if course_details
            else f"Course ID {course_id}"
        )

        # Email sending
        email_sent = send_enrollment_email(
            recipient_email=current_user.email,
            student_name=current_user.name,
            course_name=course_name,
        )
        if not email_sent:
            app.logger.error(
                f"Failed to send enrollment email to {current_user.email} for course {course_id}, but enrollment succeeded."
            )

        return jsonify(message="Enrollment successful")
    else:
        app.logger.error(
            f"Database error during enrollment for user {user_id} in course {course_id}"
        )
        return jsonify(
            message="Enrollment failed due to a database error."
        ), 500


@app.route("/api/disenroll", methods=["POST"])
@login_required
def disenroll_course():
    data = request.get_json()
    if not data or "courseId" not in data:
        return jsonify(message="Missing courseId."), 400

    try:
        course_id = int(data["courseId"])
    except ValueError:
        return jsonify(message="Invalid courseId format."), 400

    user_id = current_user.id
    success, message = database.disenroll_user_from_course(user_id, course_id)

    if success:
        app.logger.info(
            f"User {user_id} disenrolled from course {course_id}: {message}"
        )
        return jsonify(message=message), 200
    else:
        app.logger.error(
            f"Disenrollment failed for user {user_id}, course {course_id}: {message}"
        )
        return jsonify(message=message), 500


@app.route("/api/course/finish", methods=["POST"])
@login_required
def finish_course():
    data = request.get_json()
    if not data or "courseId" not in data:
        return jsonify(message="Missing courseId."), 400

    try:
        course_id = int(data["courseId"])
    except ValueError:
        return jsonify(message="Invalid courseId format."), 400

    user_id = current_user.id
    success, message = database.mark_enrollment_as_finished(user_id, course_id)

    if success:
        app.logger.info(
            f"Course {course_id} marked as finished for user {user_id}: {message}"
        )
        return jsonify(message=message), 200
    else:
        app.logger.error(
            f"Failed to mark course {course_id} as finished for user {user_id}: {message}"
        )
        if (
            "Course not found" in message
            or "already marked as finished" in message
        ):  # Cas où ce n'est pas une erreur serveur
            return jsonify(
                message=message
            ), 400  # Bad Request (ou 404 si "not found")
        return jsonify(
            message="Failed to mark course as finished due to a server error."
        ), 500


@app.route("/create_hash/<password>")
def create_hash(password):
    # **NEVER expose this in production**
    # Utilise la même méthode de hachage que database.create_user
    return generate_password_hash(password, method="pbkdf2:sha256")


if __name__ == "__main__":
    # Port 5001 comme dans votre fichier original.
    # Ajout de use_reloader=False si debug=True pour éviter certains problèmes avec le logging multiple au démarrage
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
        use_reloader=False
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true"
        else True,
    )
