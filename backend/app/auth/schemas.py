"""Request/response models for the auth + sync API.

Kept separate from `app.models.schemas` (whisky domain) so auth stays isolated.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

# EmailStr requires `email-validator`; avoid the extra dependency and validate
# with a lightweight regex instead.
class AuthRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str
    display_name: Optional[str] = None
    age_country: Optional[str] = None
    age_min: Optional[int] = None
    privacy_consent: bool = False

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("invalid email address")
        return v

    @field_validator("password")
    @classmethod
    def _strong_enough(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthVerifyEmailRequest(BaseModel):
    user_id: int
    token: str = Field(min_length=8)


class AuthUpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=100)


class SyncRow(BaseModel):
    # Empty placeholder payload; per-kind rows carry their own columns.
    pass


class SyncRequest(BaseModel):
    favorites: List[Dict[str, Any]] = Field(default_factory=list)
    scores: List[Dict[str, Any]] = Field(default_factory=list)
    notes: List[Dict[str, Any]] = Field(default_factory=list)
    lists: List[Dict[str, Any]] = Field(default_factory=list)
    items: List[Dict[str, Any]] = Field(default_factory=list)
