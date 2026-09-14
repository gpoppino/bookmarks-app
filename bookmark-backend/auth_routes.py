"""Authentication and bot-token API routes."""

from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

import config
from auth import BOT_TOKEN_PREFIX, as_utc, create_access_token, get_current_user
from auth import hash_bot_token, hash_password, serialize_bot_token
from auth import session_cookie_scope, verify_password
from database import get_db
from models import BotTokenDB, UserDB
from password_policy import PasswordPolicyError, validate_password
from schemas import BotTokenRequest, ChangePasswordRequest
from schemas import UserLoginRequest, UserRegisterRequest


router = APIRouter(prefix="/api/auth")


def enforce_password_policy(password: str) -> None:
    try:
        validate_password(password)
    except PasswordPolicyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/register", status_code=201)
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(UserDB).filter(UserDB.username == request.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")
    enforce_password_policy(request.password)
    user = UserDB(username=request.username, hashed_password=hash_password(request.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "created_at": as_utc(user.created_at)}


@router.post("/login")
async def login(request: UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == request.username).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(
        {"sub": user.username}, timedelta(days=config.ACCESS_TOKEN_EXPIRE_DAYS)
    )
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=token,
        max_age=config.SESSION_COOKIE_MAX_AGE,
        **session_cookie_scope(),
    )
    return {"id": user.id, "username": user.username, "created_at": as_utc(user.created_at)}


@router.post("/bot-tokens", status_code=201)
async def create_bot_token(
    request: BotTokenRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    raw_token = BOT_TOKEN_PREFIX + secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    stored = BotTokenDB(
        user_id=current_user.id,
        name=request.name,
        token_hash=hash_bot_token(raw_token),
        created_at=now,
        expires_at=(
            now + timedelta(days=request.expires_in_days)
            if request.expires_in_days is not None
            else None
        ),
    )
    db.add(stored)
    db.commit()
    db.refresh(stored)
    response.headers["Cache-Control"] = "no-store"
    return {**serialize_bot_token(stored), "token": raw_token}


@router.get("/bot-tokens")
async def list_bot_tokens(
    response: Response,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"
    tokens = (
        db.query(BotTokenDB)
        .filter(BotTokenDB.user_id == current_user.id)
        .order_by(BotTokenDB.id.desc())
        .all()
    )
    return [serialize_bot_token(token) for token in tokens]


@router.delete("/bot-tokens/{token_id}", status_code=204)
async def revoke_bot_token(
    token_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    token = (
        db.query(BotTokenDB)
        .filter(BotTokenDB.id == token_id, BotTokenDB.user_id == current_user.id)
        .first()
    )
    if token is None:
        raise HTTPException(status_code=404, detail="Bot token not found")
    if token.revoked_at is None:
        token.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=config.SESSION_COOKIE_NAME, **session_cookie_scope())
    return {"success": True}


@router.get("/me")
async def me(current_user: UserDB = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username,
            "created_at": as_utc(current_user.created_at)}


@router.put("/password")
async def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    enforce_password_policy(request.new_password)
    current_user.hashed_password = hash_password(request.new_password)
    db.commit()
    return {"message": "Password updated successfully"}
