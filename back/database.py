# database.py
import logging
import mysql.connector
from mysql.connector import Error
from werkzeug.security import (
    generate_password_hash,
)  # generate_password_hash est utilisé dans create_user
from config import config

logging.basicConfig(level=logging.INFO)
# logging.getLogger('mysql.connector').setLevel(logging.WARNING) # Optionnel: pour réduire le bruit du connecteur


def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            # connection_timeout=10 # Optionnel: ajouter un timeout
        )
        # Commentaire : le log "Successfully connected" peut devenir bruyant.
        # if connection.is_connected():
        #     logging.info("Successfully connected to database")
        return connection
    except Error as e:
        logging.error("Error connecting to MySQL Database: %s", e)
        return None


def _execute_query(
    query,
    params=None,
    fetch_one=False,
    fetch_all=False,
    is_ddl_dml=False,
    dictionary_cursor=True,
):
    """Helper function to execute queries and manage connections."""
    conn = get_db_connection()
    if not conn:
        # Si c'est une requête qui modifie des données, l'échec de connexion est critique
        return (False, "Database connection error") if is_ddl_dml else None

    cursor = None
    try:
        cursor = conn.cursor(
            dictionary=dictionary_cursor
        )  # Utiliser dictionary=True par défaut
        cursor.execute(query, params)

        if is_ddl_dml:  # INSERT, UPDATE, DELETE, CREATE, ALTER
            conn.commit()
            # Pour INSERT, on pourrait retourner lastrowid, pour UPDATE/DELETE, rowcount
            return True, (
                cursor.lastrowid
                if query.strip().upper().startswith("INSERT")
                else cursor.rowcount
            )

        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        # Si ni fetch_one ni fetch_all, et pas DDL/DML, c'est une opération sans résultat attendu (rare)
        return None

    except Error as e:
        if conn and is_ddl_dml:
            conn.rollback()
        logging.error(
            f"Database query error: {e}\nQuery: {query}\nParams: {params}"
        )
        return (False, f"Database error: {e}") if is_ddl_dml else None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def create_user(name, email, password_text):
    # ... (code existant, semble correct mais utilise une connexion/curseur direct)
    # Pourrait être refactorisé pour utiliser _execute_query si on veut une consistance
    # mais la logique de vérification d'email existant est spécifique ici.
    # Le hachage est fait ici, ce qui est bien.
    conn = get_db_connection()
    if not conn:
        logging.error("Database connection failed, cannot create user.")
        return False, "Database connection error."

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        check_query = "SELECT user_id FROM users WHERE email = %s"
        cursor.execute(check_query, (email,))
        if cursor.fetchone():
            logging.warning(
                f"Attempt to create user with existing email: {email}"
            )
            return False, "Email already exists."

        password_hash = generate_password_hash(
            password_text, method="pbkdf2:sha256"
        )
        insert_query = (
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)"
        )
        cursor.execute(insert_query, (name, email, password_hash))
        conn.commit()
        logging.info(f"User created successfully: {email}")
        return True, "User created successfully."
    except Error as e:
        logging.error(f"Error creating user {email}: {e}")
        if conn:
            conn.rollback()
        return False, f"Database error: {e}"
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def find_user_by_email(email):
    # Correction: la query était mal indentée si conn était None (n'affectait pas la logique mais propre)
    query = (
        "SELECT user_id, email, name, password_hash FROM users WHERE email = %s"
    )
    return _execute_query(query, (email,), fetch_one=True)


def find_user_by_id(user_id):
    query = "SELECT user_id, email, name FROM users WHERE user_id = %s"
    return _execute_query(query, (user_id,), fetch_one=True)


def get_enrolled_courses(user_id):
    query = """
        SELECT c.course_id, c.name, c.description 
        FROM courses c
        JOIN enrollments e ON c.course_id = e.course_id
        WHERE e.user_id = %s AND e.status = 'enrolled'
    """
    return _execute_query(query, (user_id,), fetch_all=True)


def get_available_courses(user_id):
    # Cette logique est un peu plus complexe et peut rester avec sa propre gestion de curseur
    # ou être décomposée si on utilise _execute_query.
    # Gardons-la telle quelle pour l'instant, elle fonctionne.
    conn = get_db_connection()
    if not conn:
        return []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        enrolled_query = "SELECT course_id FROM enrollments WHERE user_id = %s"
        cursor.execute(enrolled_query, (user_id,))
        enrolled_ids = [row["course_id"] for row in cursor.fetchall()]

        available_query = "SELECT course_id, name, description FROM courses"
        params = []
        if enrolled_ids:
            placeholders = ", ".join(["%s"] * len(enrolled_ids))
            available_query += f" WHERE course_id NOT IN ({placeholders})"
            params.extend(enrolled_ids)

        cursor.execute(
            available_query, tuple(params)
        )  # S'assurer que params est un tuple
        courses = cursor.fetchall()
        return courses
    except Error as e:
        logging.error(f"Error fetching available courses: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def check_if_enrolled(user_id, course_id):
    query = "SELECT 1 FROM enrollments WHERE user_id = %s AND course_id = %s AND status = 'enrolled' LIMIT 1"
    # Ajout de status = 'enrolled' pour être précis
    result = _execute_query(
        query, (user_id, course_id), fetch_one=True, dictionary_cursor=False
    )  # Pas besoin de dict ici
    return result is not None


def enroll_user_in_course(user_id, course_id):
    # Assure que le statut est 'enrolled' par défaut ou explicitement
    # La table a DEFAULT 'enrolled' pour status, donc c'est bon.
    query = "INSERT INTO enrollments (user_id, course_id, enrollment_date, status) VALUES (%s, %s, NOW(), 'enrolled')"
    # On s'assure de mettre le statut 'enrolled' en cas de réinscription après désinscription
    # ou si le DEFAULT n'était pas appliqué pour une raison.
    # Alternative plus robuste : INSERT ... ON DUPLICATE KEY UPDATE status='enrolled', enrollment_date=NOW()
    # Cela nécessiterait une clé unique sur (user_id, course_id) dans la table `enrollments` ce qui est déjà fait.
    # L'actuel `check_if_enrolled` dans app.py empêche déjà l'appel à cette fonction si déjà inscrit.
    # Donc, un simple INSERT est suffisant.
    success, _ = _execute_query(query, (user_id, course_id), is_ddl_dml=True)
    return success


def disenroll_user_from_course(user_id, course_id):
    # La logique actuelle avec vérification préalable est bonne.
    # On pourrait utiliser _execute_query pour le DELETE mais la logique de vérification est spécifique.
    conn = get_db_connection()
    if not conn:
        logging.error("Database connection failed, cannot disenroll user.")
        return False, "Database connection error."

    cursor = None
    try:
        cursor = conn.cursor(
            dictionary=False
        )  # Pas besoin de dict pour ces opérations
        check_query = "SELECT 1 FROM enrollments WHERE user_id = %s AND course_id = %s"  # Vérifie l'existence de l'inscription, peu importe le statut
        cursor.execute(check_query, (user_id, course_id))
        if not cursor.fetchone():
            logging.warning(
                f"User {user_id} has no enrollment record for course {course_id}, disenrollment requested."
            )
            return (
                True,
                "No enrollment record found for this course.",
            )  # L'état final est "non inscrit"

        delete_query = (
            "DELETE FROM enrollments WHERE user_id = %s AND course_id = %s"
        )
        cursor.execute(delete_query, (user_id, course_id))

        if cursor.rowcount > 0:
            conn.commit()
            logging.info(
                f"User {user_id} disenrolled successfully from course {course_id}"
            )
            return True, "Successfully disenrolled."
        else:
            # Devrait être attrapé par la vérification ci-dessus, mais sécurité
            logging.warning(
                f"No enrollment found to delete for user {user_id} and course {course_id} (should have been caught)."
            )
            return True, "No active enrollment found to remove."
    except Error as e:
        logging.error(
            f"Error disenrolling user {user_id} from course {course_id}: {e}"
        )
        if conn:
            conn.rollback()
        return False, f"Database error: {e}"
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_finished_courses(user_id):
    query = """
        SELECT c.course_id, c.name, c.description 
        FROM courses c
        JOIN enrollments e ON c.course_id = e.course_id
        WHERE e.user_id = %s AND e.status = 'finished'
    """
    return _execute_query(query, (user_id,), fetch_all=True)


def mark_enrollment_as_finished(user_id, course_id):
    # La logique actuelle est bonne.
    conn = (
        get_db_connection()
    )  # Gardons la connexion/curseur direct pour cette logique spécifique
    if not conn:
        logging.error(
            "Database connection failed, cannot mark course as finished."
        )
        return False, "Database connection error."

    cursor = None
    try:
        cursor = conn.cursor(dictionary=False)  # Pas besoin de dict
        update_query = """
            UPDATE enrollments 
            SET status = 'finished' 
            WHERE user_id = %s AND course_id = %s AND status = 'enrolled'
        """
        cursor.execute(update_query, (user_id, course_id))

        if cursor.rowcount > 0:
            conn.commit()
            logging.info(
                f"Course {course_id} marked as finished for user {user_id}."
            )
            return True, "Course marked as finished."
        else:
            cursor.execute(
                "SELECT status FROM enrollments WHERE user_id = %s AND course_id = %s",
                (user_id, course_id),
            )
            result = cursor.fetchone()
            if result and result[0] == "finished":
                return True, "Course was already marked as finished."
            return (
                False,
                "Course not found or not currently 'enrolled' to be marked as finished.",
            )

    except Error as e:
        logging.error(
            f"Error marking course {course_id} as finished for user {user_id}: {e}"
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
    query = (
        "SELECT course_id, name, description FROM courses WHERE course_id = %s"
    )
    return _execute_query(query, (course_id,), fetch_one=True)
