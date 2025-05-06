"""Email_utils.py."""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from config import config


def send_enrollment_email(recipient_email, student_name, course_name):
    """Send an enrollment confirmation email."""
    if not all(
        [
            config.SMTP_SERVER,
            config.SMTP_USER,
            config.SMTP_PASSWORD,
            config.SENDER_EMAIL,
        ]
    ):
        logging.warning("SMTP settings incomplete. Skipping email sending.")
        return False

    subject = f"Course Enrollment Confirmation: {course_name}"
    body = f"""
    Hi {student_name},

    You have successfully enrolled in the course: {course_name}.

    You can find the course materials [here: https://www.coursera.org/]

    Happy learning!

    Student Portal Team
    """

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = config.SENDER_EMAIL
    msg["To"] = recipient_email

    try:
        # Create a secure SSL context
        context = ssl.create_default_context()

        # Try connecting using STARTTLS (standard for port 587)
        if config.SMTP_USE_TLS:
            server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
            server.starttls(context=context)  # Secure the connection
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            logging.info(
                "Enrollment email sent successfully to %s", recipient_email
            )
            return True
        else:  # For older SSL connections (usually port 465, less common now)
            with smtplib.SMTP_SSL(
                config.SMTP_SERVER, config.SMTP_PORT, context=context
            ) as server:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
                server.send_message(msg)
                logging.info(
                    "Enrollment email sent successfully to %s", recipient_email
                )
                return True

    except smtplib.SMTPAuthenticationError as e:
        logging.error(
            "SMTP Authentication Error sending email: %s. "
            "Check SMTP credentials.",
            e,
        )
        return False
    except (smtplib.SMTPException, ssl.SSLError, ConnectionError) as e:
        logging.error("SMTP or connection error sending email: %s", e)
        return False
