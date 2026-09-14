"""Password validation shared by registration and password changes."""

import unicodedata


MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_BYTES = 72


class PasswordPolicyError(ValueError):
    """Raised when a password does not satisfy the application policy."""


def validate_password(password: str) -> None:
    """Validate a password without modifying or normalizing the supplied secret."""
    if password.isspace():
        raise PasswordPolicyError("Password cannot consist only of whitespace")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
        )
    if any(unicodedata.category(character) == "Cc" for character in password):
        raise PasswordPolicyError("Password cannot contain control characters")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise PasswordPolicyError(
            f"Password must not exceed {MAX_PASSWORD_BYTES} UTF-8 bytes"
        )
