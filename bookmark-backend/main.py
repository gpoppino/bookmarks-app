"""FastAPI application composition root.

Compatibility re-exports keep existing scripts and tests working while implementation
details live in focused modules.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import bookmark_routes
import bookmark_service
import config
from auth import (
    BOT_TOKEN_PREFIX,
    BOT_TOKEN_SCOPE,
    as_utc,
    create_access_token,
    get_bookmark_creator,
    get_current_user,
    hash_bot_token,
    hash_password,
    serialize_bot_token,
    session_cookie_scope,
    verify_password,
)
from auth_routes import router as auth_router
from bookmark_routes import router as bookmark_router
from bookmark_service import (
    attach_tags,
    get_automatic_tags,
    get_user_tag_names,
    serialize_bookmark,
    tag_suggester,
)
from config import (
    ACCESS_TOKEN_EXPIRE_DAYS,
    ALGORITHM,
    DATABASE_URL,
    ENVIRONMENT,
    SECRET_KEY,
    SESSION_COOKIE_DOMAIN,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_MAX_AGE,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_PATH,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
    load_secret_key,
    load_tagging_environment,
    read_secret_key,
    read_systemd_credential,
)
from database import Base, SQLALCHEMY_DATABASE_URL, SessionLocal, engine, get_db
from metadata import fetch_bookmark_metadata
from models import BookmarkDB, BotTokenDB, TagDB, UserDB, bookmark_tag_association
from schemas import (
    BookmarkRequest,
    BookmarkUpdateRequest,
    BotTokenRequest,
    ChangePasswordRequest,
    UserLoginRequest,
    UserRegisterRequest,
)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bookmarks API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(bookmark_router)
