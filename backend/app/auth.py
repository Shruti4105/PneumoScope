"""Simple email + password login.

Passwords are hashed with bcrypt. A signed session token is stored in an
HttpOnly, SameSite=Lax cookie, so JavaScript never sees it.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User

COOKIE = "pneumoscope_session"
router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------- helpers
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt(rounds=12)).decode()


def check_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except ValueError:
        return False


def _token(user_id: int) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(hours=s.session_hours)
    return jwt.encode({"sub": str(user_id), "exp": exp}, s.get_secret_key(), algorithm="HS256")


def _set_cookie(resp: Response, user: User, remember: bool = True) -> None:
    """remember=False gives a browser-session cookie that is cleared when the browser closes."""
    s = get_settings()
    resp.set_cookie(COOKIE, _token(user.id), httponly=True, samesite="lax", secure=s.cookie_secure,
                    max_age=s.session_hours * 3600 if remember else None, path="/")


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.")
    try:
        payload = jwt.decode(token, get_settings().get_secret_key(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please sign in again.")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.")
    return user


def ensure_admin(db: Session) -> None:
    """Create the optional first account from ADMIN_EMAIL / ADMIN_PASSWORD."""
    s = get_settings()
    if s.admin_email and s.admin_password:
        email = s.admin_email.lower()
        if not db.scalar(select(User).where(User.email == email)):
            db.add(User(email=email, name=s.admin_name, password_hash=hash_password(s.admin_password)))
            db.commit()


# ---------------------------------------------------------------- schemas
class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)
    remember: bool = True


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def strong(cls, v: str) -> str:
        if len(v) < 8 or len(v.encode()) > 72 or not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must be 8–72 characters with at least one letter and one number.")
        return v


class UserOut(BaseModel):
    id: int
    name: str
    email: str


# ---------------------------------------------------------------- routes
@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not check_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    _set_cookie(response, user, body.remember)
    return UserOut(id=user.id, name=user.name, email=user.email)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = User(email=email, name=" ".join(body.name.split()), password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    _set_cookie(response, user)
    return UserOut(id=user.id, name=user.name, email=user.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return UserOut(id=user.id, name=user.name, email=user.email)
