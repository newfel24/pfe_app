"""Models.py."""

from flask_login import UserMixin


class User(UserMixin):
    """User class for Flask-Login."""

    def __init__(self, user_data):
        """Initialize a new User instance.

        Args:
            user_data (dict): Dictionary containing user information with keys:
                            'user_id', 'email', and optionally 'name'
        """
        self.id = user_data["user_id"]  # Must have 'id' attribute
        self.email = user_data["email"]
        self.name = user_data.get("name", "User")  # Optional name field

    # You might add other methods if needed
