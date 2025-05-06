# database.py
import mysql.connector
from mysql.connector import Error
from config import config
import logging # For logging DB errors

logging.basicConfig(level=logging.INFO)


# --- Connection ---
def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )
        if connection.is_connected():
            # logging.info("Successfully connected to database")
            return connection
    except Error as e:
        logging.error(f"Error connecting to MySQL Database: {e}")
        return None


# --- User Queries ---
def find_user_by_email(email):
    """Finds a user by email and returns user data including id, email, name, password_hash."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True) # Returns rows as dictionaries
        query = "SELECT user_id, email, name, password_hash FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        return user # Returns dict or None
    except Error as e:
        logging.error(f"Error finding user by email: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def find_user_by_id(user_id):
    """Finds a user by ID for Flask-Login user_loader."""
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT user_id, email, name FROM users WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        return user
    except Error as e:
        logging.error(f"Error finding user by ID: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# --- Course/Enrollment Queries ---
def get_enrolled_courses(user_id):
    """Gets courses a specific user is enrolled in."""
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT c.course_id, c.name, c.description
            FROM courses c
            JOIN enrollments e ON c.course_id = e.course_id
            WHERE e.user_id = %s
        """
        cursor.execute(query, (user_id,))
        courses = cursor.fetchall()
        return courses # Returns list of dicts
    except Error as e:
        logging.error(f"Error fetching enrolled courses: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_available_courses(user_id):
    """Gets courses a specific user is NOT enrolled in."""
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        # Find course IDs the user *is* enrolled in
        enrolled_query = "SELECT course_id FROM enrollments WHERE user_id = %s"
        cursor.execute(enrolled_query, (user_id,))
        enrolled_ids = [row['course_id'] for row in cursor.fetchall()]

        # Fetch all courses excluding the enrolled ones
        if enrolled_ids:
            # Create placeholders string like '%s, %s, %s'
            placeholders = ', '.join(['%s'] * len(enrolled_ids))
            available_query = f"SELECT course_id, name, description FROM courses WHERE course_id NOT IN ({placeholders})"
            cursor.execute(available_query, tuple(enrolled_ids))
        else:
            # If user is enrolled in nothing, fetch all courses
            available_query = "SELECT course_id, name, description FROM courses"
            cursor.execute(available_query)

        courses = cursor.fetchall()
        return courses # Returns list of dicts
    except Error as e:
        logging.error(f"Error fetching available courses: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def check_if_enrolled(user_id, course_id):
    """Checks if a user is already enrolled in a specific course."""
    conn = get_db_connection()
    if not conn: return False # Assume not enrolled if DB error
    try:
        cursor = conn.cursor()
        query = "SELECT 1 FROM enrollments WHERE user_id = %s AND course_id = %s LIMIT 1"
        cursor.execute(query, (user_id, course_id))
        return cursor.fetchone() is not None # True if a row exists, False otherwise
    except Error as e:
        logging.error(f"Error checking enrollment status: {e}")
        return False # Safer to assume not enrolled on error
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def enroll_user_in_course(user_id, course_id):
    """Adds an enrollment record to the database."""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO enrollments (user_id, course_id, enrollment_date) 
            VALUES (%s, %s, NOW()) 
        """
        # Note: NOW() gets the current timestamp from the MySQL server
        cursor.execute(query, (user_id, course_id))
        conn.commit() # Commit the transaction
        return True # Success
    except Error as e:
        logging.error(f"Error enrolling user in course: {e}")
        conn.rollback() # Rollback on error
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            
def get_course_details(course_id):
    """Fetches details for a single course by ID."""
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT course_id, name, description FROM courses WHERE course_id = %s"
        cursor.execute(query, (course_id,))
        course = cursor.fetchone()
        return course
    except Error as e:
        logging.error(f"Error fetching course details: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
