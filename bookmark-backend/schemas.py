"""Request schemas for the HTTP API."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class BookmarkRequest(BaseModel):
    url: str
    tags: List[str] = []


class BookmarkUpdateRequest(BaseModel):
    url: Optional[str] = None
    tags: Optional[List[str]] = None


class UserRegisterRequest(BaseModel):
    username: str
    password: str


class UserLoginRequest(BaseModel):
    username: str
    password: str


class BotTokenRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3650)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
