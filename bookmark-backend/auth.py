"""Authentication helpers and FastAPI dependencies."""

from datetime import datetime, timedelta, timezone
import hashlib

import bcrypt as bcrypt_lib
from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import config
from database import get_db
from models import BotTokenDB, UserDB


BOT_TOKEN_PREFIX = "bkt_"
BOT_TOKEN_SCOPE = "bookmarks:create"


def hash_password(password: str) -> str:
    return bcrypt_lib.hashpw(password.encode(), bcrypt_lib.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt_lib.checkpw(plain.encode(), hashed.encode())


def session_cookie_scope() -> dict:
    """Return attributes that must match when setting or deleting the cookie."""
    return {
        "path": config.SESSION_COOKIE_PATH,
        "domain": config.SESSION_COOKIE_DOMAIN,
        "secure": config.SESSION_COOKIE_SECURE,
        "httponly": config.SESSION_COOKIE_HTTPONLY,
        "samesite": config.SESSION_COOKIE_SAMESITE,
    }


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> UserDB:
    if request.headers.get("Authorization") is not None:
        raise HTTPException(status_code=401, detail="Session login required")
    token = request.cookies.get(config.SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def hash_bot_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def as_utc(value: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC). SQLite stores naive datetimes."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def get_bookmark_creator(request: Request, db: Session = Depends(get_db)) -> UserDB:
    authorization = request.headers.get("Authorization")
    if authorization is not None:
        scheme, separator, token = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="Invalid bot token")
    else:
        token = request.cookies.get(config.SESSION_COOKIE_NAME, "")
        if not token.startswith(BOT_TOKEN_PREFIX):
            return get_current_user(request, db)

    if not token.startswith(BOT_TOKEN_PREFIX) or len(token) != 47:
        raise HTTPException(status_code=401, detail="Invalid bot token")
    stored = db.query(BotTokenDB).filter(
        BotTokenDB.token_hash == hash_bot_token(token)
    ).first()
    now = datetime.now(timezone.utc)
    if (
        stored is None
        or stored.revoked_at is not None
        or (stored.expires_at is not None and as_utc(stored.expires_at) <= now)
    ):
        raise HTTPException(status_code=401, detail="Invalid bot token")
    user = db.query(UserDB).filter(UserDB.id == stored.user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid bot token")
    stored.last_used_at = now
    db.commit()
    return user


def serialize_bot_token(token: BotTokenDB) -> dict:
    return {
        "id": token.id,
        "name": token.name,
        "scope": BOT_TOKEN_SCOPE,
        "created_at": as_utc(token.created_at),
        "expires_at": as_utc(token.expires_at),
        "revoked_at": as_utc(token.revoked_at),
        "last_used_at": as_utc(token.last_used_at),
    }
