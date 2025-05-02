"""A Flask application that provides an email sending service via SMTP."""

import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText

from flask import Flask, request, jsonify

app = Flask(__name__)

load_dotenv()

# Hardcoded sender credentials (use secure vaults in production)
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
print(SENDER_EMAIL, SENDER_PASSWORD)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify if the service is running.
    Returns a simple JSON response indicating the service status.
    """
    return jsonify({"status": "ok"}), 200


@app.route("/send-email", methods=["POST"])
def send_email():
    """
    Send an email using SMTP server.

    Expects a JSON payload with 'to', 'subject', and 'message' fields.
    Returns a success message or error details.
    """
    data = request.get_json()
    recipient = data.get("to")
    subject = data.get("subject")
    body = data.get("message")

    if not all([recipient, subject, body]):
        return jsonify({"error": "Missing fields in request"}), 400

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient, msg.as_string())

        return jsonify({"message": "Email sent successfully"}), 200

    except smtplib.SMTPException as e:
        return jsonify({"error": f"SMTP error occurred: {str(e)}"}), 500
    except ConnectionError as e:
        return jsonify({"error": f"Connection error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)
