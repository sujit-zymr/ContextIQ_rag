import os
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from psycopg.errors import UniqueViolation

from app.database.user_repository import create_user, get_user_by_email, get_user_by_id
from app.api.schemas import RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
password_hash = PasswordHash.recommended()
TOKEN_TTL_SECONDS = 30 * 60
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _secret_key():
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret or len(secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET_KEY must be configured with at least 32 characters.",
        )
    return secret


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    _secret_key()
    email = payload.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=422, detail="A valid email address is required.")
    try:
        user = create_user(email, password_hash.hash(payload.password))
    except UniqueViolation as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
    return UserResponse(id=user[0], email=user[1], created_at=user[2])


@router.post("/token", response_model=TokenResponse)
def issue_token(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    secret = _secret_key()
    user = get_user_by_email(form.username.strip().lower())
    if user is None or not password_hash.verify(form.password, user[2]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL_SECONDS)
    token = jwt.encode(
        {"sub": str(user[0]), "exp": expires_at},
        secret,
        algorithm="HS256",
    )
    return TokenResponse(access_token=token, expires_in=TOKEN_TTL_SECONDS)


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(
            token,
            _secret_key(),
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
        user_id = payload.get("sub")
        user = get_user_by_id(user_id)
    except (InvalidTokenError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"id": user[0], "email": user[1], "created_at": user[2]}


@router.get("/me", response_model=UserResponse)
def current_user_profile(user: Annotated[dict, Depends(get_current_user)]):
    return UserResponse(id=user["id"], email=user["email"], created_at=user["created_at"])
