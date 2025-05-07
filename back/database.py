"""Database module for handling MySQL database operations and queries."""

import logging  # For logging DB errors

import mysql.connector
from config import config
from mysql.connector import Error
from werkzeug.security import generate_password_hash


logging.basicConfig(level=logging.INFO)


# --- Connection ---
def get_db_connection():
    """Establish a connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
        )
        if connection.is_connected():
            logging.info("Successfully connected to database")
            return connection
    except Error as e:
        logging.error("Error connecting to MySQL Database: %s", e)
        return None


# --- User Queries ---
def create_user(name, email, password_text):
    """Creates a new user in the database with a hashed password."""
    conn = get_db_connection()
    if not conn:
        logging.error("Database connection failed, cannot create user.")
        return False, "Database connection error."

    try:
        cursor = conn.cursor(
            dictionary=True
        )  # Assurez-vous que dictionary=True est utilisé si vous voulez
        # vérifier les doublons d'une certaine manière

        # 1. Vérifier si l'email existe déjà
        check_query = "SELECT user_id FROM users WHERE email = %s"
        cursor.execute(check_query, (email,))
        if cursor.fetchone():
            logging.warning(
                "Attempt to create user with existing email: %s", email
            )
            return False, "Email already exists."

        # 2. Hasher le mot de passe
        password_hash = generate_password_hash(
            password_text, method="pbkdf2:sha256"
        )

        # 3. Insérer le nouvel utilisateur
        insert_query = (
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)"
        )
        cursor.execute(insert_query, (name, email, password_hash))
        conn.commit()
        logging.info("User created successfully: %s", email)
        return True, "User created successfully."
    except Error as e:
        logging.error("Error creating user %s: %s", email, e)
        conn.rollback()
        return False, f"Database error: {e}"  # Ou un message plus générique
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def find_user_by_email(email):
    """Find a user by email and return user data.

    Returns id, email, name, and password_hash.
    """
    conn = get_db_connection()
    if not conn:
        query = """
            SELECT user_id, email, name, password_hash
            FROM users
            WHERE email = %s"""
    try:
        cursor = conn.cursor(dictionary=True)  # Returns rows as dictionaries
        query = (
            "SELECT user_id, email, name, password_hash "
            "FROM users WHERE email = %s"
        )
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        return user  # Returns dict or None
    except Error as e:
        logging.error("Error finding user by email: %s", e)
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def find_user_by_id(user_id):
    """Find a user by ID for Flask-Login user_loader."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT user_id, email, name FROM users WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        return user
    except Error as e:
        logging.error("Error finding user by ID: %s", e)
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# --- Course/Enrollment Queries ---
def get_enrolled_courses(user_id):
    """Gets courses a specific user is actively enrolled in."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        # MODIFICATION: Ajouter la condition sur le statut
        query = """
            SELECT c.course_id, c.name, c.description
            FROM courses c
            JOIN enrollments e ON c.course_id = e.course_id
            WHERE e.user_id = %s AND e.status = 'enrolled'
        """
        cursor.execute(query, (user_id,))
        courses = cursor.fetchall()
        return courses
    except Error as e:
        logging.error("Error fetching enrolled courses: %s", e)
        return []
    finally:
        if (
            conn and conn.is_connected()
        ):  # Vérifier conn avant d'appeler is_connected
            if "cursor" in locals() and cursor:
                cursor.close()
            conn.close()


def get_available_courses(user_id):
    """Get courses a specific user is NOT enrolled in."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        # Find course IDs the user *is* enrolled in
        enrolled_query = "SELECT course_id FROM enrollments WHERE user_id = %s"
        cursor.execute(enrolled_query, (user_id,))
        enrolled_ids = [row["course_id"] for row in cursor.fetchall()]

        # Fetch all courses excluding the enrolled ones
        if enrolled_ids:
            # Create placeholders string like '%s, %s, %s'
            placeholders = ", ".join(["%s"] * len(enrolled_ids))
            available_query = (
                f"SELECT course_id, name, description FROM courses "
                f"WHERE course_id NOT IN ({placeholders})"
            )
            cursor.execute(available_query, tuple(enrolled_ids))
        else:
            # If user is enrolled in nothing, fetch all courses
            available_query = "SELECT course_id, name, description FROM courses"
            cursor.execute(available_query)

        courses = cursor.fetchall()
        return courses  # Returns list of dicts
    except Error as e:
        logging.error("Error fetching available courses: %s", e)
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def check_if_enrolled(user_id, course_id):
    """Check if a user is already enrolled in a specific course."""
    conn = get_db_connection()
    if not conn:
        return False  # Assume not enrolled if DB error
    try:
        cursor = conn.cursor()
        query = (
            "SELECT 1 FROM enrollments "
            "WHERE user_id = %s AND course_id = %s LIMIT 1"
        )
        cursor.execute(query, (user_id, course_id))
        # True if a row exists, False otherwise
        return cursor.fetchone() is not None
    except Error as e:
        logging.error("Error checking enrollment status: %s", e)
        return False  # Safer to assume not enrolled on error
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def enroll_user_in_course(user_id, course_id):
    """Add an enrollment record to the database."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO enrollments (user_id, course_id, enrollment_date)
            VALUES (%s, %s, NOW())
        """
        # Note: NOW() gets the current timestamp from the MySQL server
        cursor.execute(query, (user_id, course_id))
        conn.commit()  # Commit the transaction
        return True  # Success
    except Error as e:
        logging.error("Error enrolling user in course: %s", e)
        conn.rollback()  # Rollback on error
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def disenroll_user_from_course(user_id, course_id):
    """Removes an enrollment record from the database."""
    conn = get_db_connection()
    if not conn:
        logging.error("Database connection failed, cannot disenroll user.")
        return False, "Database connection error."

    cursor = None  # Initialiser cursor à None
    try:
        cursor = conn.cursor()
        # Vérifier d'abord si l'inscription existe pour donner un retour
        # plus précis
        check_query = (
            "SELECT 1 FROM enrollments WHERE user_id = %s AND course_id = %s"
        )
        cursor.execute(check_query, (user_id, course_id))
        if not cursor.fetchone():
            logging.warning(
                "User %s not enrolled in course %s, disenrollment requested.",
                user_id,
                course_id,
            )
            # On pourrait considérer cela comme un succès
            # car l'état final est "non inscrit"
            # ou retourner un message spécifique. Pour l'instant, on supprime
            # si ça existe.
            return True, "User was not enrolled or already disenrolled."

        delete_query = (
            "DELETE FROM enrollments WHERE user_id = %s AND course_id = %s"
        )
        cursor.execute(delete_query, (user_id, course_id))

        if (
            cursor.rowcount > 0
        ):  # rowcount indique le nombre de lignes affectées
            conn.commit()  # Valider la transaction
            logging.info(
                "User %s disenrolled successfully from course %s",
                user_id,
                course_id,
            )
            return True, "Successfully disenrolled."
        else:
            # Cela ne devrait pas arriver si la vérification ci-dessus
            # a trouvé une inscription
            # mais c'est une sécurité en cas de conditions de concurrence
            # rares sans verrouillage de ligne.
            logging.warning(
                "No enrollment found for user %s and course %s "
                "during delete, though expected.",
                user_id,
                course_id,
            )
            return (
                True,
                "No active enrollment found to remove.",
            )  # Ou False si on veut signaler l'incohérence
    except Error as e:
        logging.error(
            "Error disenrolling user %s from course %s: %s",
            user_id,
            course_id,
            e,
        )
        if conn:  # S'assurer que conn existe avant de faire rollback
            conn.rollback()  # Annuler en cas d'erreur
        return False, f"Database error: {e}"
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_finished_courses(user_id):
    """Gets courses a specific user has finished."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT c.course_id, c.name, c.description
            FROM courses c
            JOIN enrollments e ON c.course_id = e.course_id
            WHERE e.user_id = %s AND e.status = 'finished'
        """
        cursor.execute(query, (user_id,))
        courses = cursor.fetchall()
        return courses
    except Error as e:
        logging.error("Error fetching finished courses: %s", e)
        return []
    finally:
        if conn and conn.is_connected():
            if "cursor" in locals() and cursor:
                cursor.close()
            conn.close()


def mark_enrollment_as_finished(user_id, course_id):
    """Marks a specific enrollment as 'finished' for a user."""
    conn = get_db_connection()
    if not conn:
        logging.error(
            "Database connection failed, cannot mark course as finished."
        )
        return False, "Database connection error."

    cursor = None
    try:
        cursor = conn.cursor()
        # S'assurer que le cours est actuellement 'enrolled' avant de le marque
        # comme 'finished'
        update_query = """
            UPDATE enrollments
            SET status = 'finished'
            WHERE user_id = %s AND course_id = %s AND status = 'enrolled'
        """
        cursor.execute(update_query, (user_id, course_id))

        if (
            cursor.rowcount > 0
        ):  # rowcount > 0 signifie que la mise à jour a eu lieu
            conn.commit()
            logging.info(
                "Course %s marked as finished for user %s", course_id, user_id
            )
            return True, "Course marked as finished."
        else:
            # Soit le cours n'était pas 'enrolled' | l'inscription n'existe pas
            logging.warning(
                "No 'enrolled' course %s found to mark as finished user %s",
                course_id,
                user_id,
            )
            # On vérifie si le cours est déjà 'finished' pour ne pas retourner
            # une erreur inutile
            check_query = (
                "SELECT status FROM enrollments "
                "WHERE user_id = %s AND course_id = %s"
            )
            cursor.execute(check_query, (user_id, course_id))
            result = cursor.fetchone()
            if result and result[0] == "finished":
                return True, "Course was already marked as finished."
            return False, "Course not found or not currently enrolled."

    except Error as e:
        logging.error(
            "Error marking course %s as finished for user %s: %s",
            course_id,
            user_id,
            e,
        )
        if conn:
            conn.rollback()
        return False, f"Database error: {e}"
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_course_details(course_id):
    """Fetch details for a single course by ID."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        query = (
            "SELECT course_id, name, description "
            "FROM courses WHERE course_id = %s"
        )
        cursor.execute(query, (course_id,))
        course = cursor.fetchone()
        return course
    except Error as e:
        logging.error("Error fetching course details: %s", e)
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
