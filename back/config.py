"""Configuration module for the application.

This module provides configuration settings management through environment
variables, including database credentials, SMTP email settings, and application
secret keys.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Configuration class for the application.

    This class manages environment variables and configuration settings for the
    application, including database credentials, SMTP email settings, and
    secret keys.
    """

    SECRET_KEY = os.getenv(
        "FLASK_SECRET_KEY", "a_default_fallback_secret_key"
    )  # Fallback only for emergencies

    # Database Configuration
    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")

    # SMTP Email Configuration
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT"))
    SMTP_USE_TLS = True  # Common practice
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")

    # Basic check for essential DB config
    if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
        print("Warning: Database configuration is incomplete!")

    # Basic check for essential Email config
    if not all([SMTP_SERVER, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL]):
        print("Warning: SMTP configuration is incomplete! Emails may fail.")


# Instantiate the config
config = Config()
