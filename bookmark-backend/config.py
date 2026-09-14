"""Runtime configuration for the bookmarks backend."""

import os
from pathlib import Path
from typing import Optional


DEVELOPMENT_ENVIRONMENT = "development"
LOCAL_DEVELOPMENT_SECRET_KEY = "dev-secret-key-change-in-production"
MIN_SECRET_KEY_LENGTH = 32
ENVIRONMENT = os.environ.get("APP_ENV", "production").strip().lower()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
SESSION_COOKIE_NAME = "access_token"
SESSION_COOKIE_PATH = "/"
SESSION_COOKIE_DOMAIN = None
SESSION_COOKIE_SAMESITE = "lax"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = ENVIRONMENT != DEVELOPMENT_ENVIRONMENT
SESSION_COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def read_systemd_credential(name: str) -> Optional[str]:
    """Read a text credential supplied to the service by systemd."""
    credentials_directory = os.environ.get("CREDENTIALS_DIRECTORY")
    if credentials_directory:
        credential_path = Path(credentials_directory) / name
        try:
            return credential_path.read_text(encoding="utf-8").rstrip("\r\n")
        except FileNotFoundError:
            pass
        except (OSError, UnicodeError) as error:
            raise RuntimeError(
                f"Unable to read systemd credential {name!r}: {credential_path}"
            ) from error
    return None


def read_secret_key() -> Optional[str]:
    """Read the JWT signing key from systemd credentials or the environment."""
    credential = read_systemd_credential("secret_key")
    if credential is not None:
        return credential
    return os.environ.get("SECRET_KEY")


def load_tagging_environment() -> dict[str, str]:
    """Build tagging configuration, preferring the systemd OpenAI credential."""
    configuration = os.environ.copy()
    credential = read_systemd_credential("openai_api_key")
    if credential is not None:
        configuration["OPENAI_API_KEY"] = credential
    return configuration


def load_secret_key() -> str:
    """Load a JWT signing key, allowing a known key only in explicit development."""
    secret_key = read_secret_key()
    if ENVIRONMENT == DEVELOPMENT_ENVIRONMENT:
        return secret_key or LOCAL_DEVELOPMENT_SECRET_KEY
    if not secret_key or not secret_key.strip():
        raise RuntimeError(
            "SECRET_KEY is required outside development. "
            "Set APP_ENV=development only for local development."
        )
    if len(secret_key) < MIN_SECRET_KEY_LENGTH:
        raise RuntimeError(
            f"SECRET_KEY must contain at least {MIN_SECRET_KEY_LENGTH} characters "
            "outside development."
        )
    if secret_key == LOCAL_DEVELOPMENT_SECRET_KEY:
        raise RuntimeError(
            "The local development SECRET_KEY cannot be used outside development."
        )
    return secret_key


SECRET_KEY = load_secret_key()
