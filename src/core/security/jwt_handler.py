"""Module for handling JWT token creation and verification in the PayU Processing Service application. This module provides functions to create access and refresh tokens, as well as to verify these tokens when they are used for authentication. The create_access_token and create_refresh_token functions generate JWT tokens with specific payloads, including expiration times, unique identifiers (jti), and token types (access or refresh). The verify_access_token and verify_refresh_token functions decode the provided tokens and validate their contents, ensuring that they are of the correct type and have not expired. Additionally, the get_current_user function retrieves the current user's information based on the token payload, allowing for secure access to user-specific data in the application."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, Request
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db
from src.config.settings import settings
from src.core.exceptions.exceptions import NotFoundException, UnauthorizedException
from src.data.models.user_model import User
from src.data.repositories.base_repository import get_data_by_id


def create_access_token(data: dict[str, Any]) -> tuple[str, str, datetime] | None:
    """Create a JWT access token with the provided data. This function takes a dictionary of data as input, creates a copy of it, and adds an expiration time (based on the configured access token expiration minutes), a unique identifier (jti), and a type field set to "access". It then encodes this information into a JWT token using the configured secret key and algorithm. The function returns a tuple containing the generated token, the jti, and the expiration time. If there is an error during token creation, it returns None."""
    try:
        to_encode = data.copy()
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
        jti = str(uuid.uuid4())

        to_encode.update({"exp": expire, "type": "access", "jti": jti})
        token = jwt.encode(to_encode, settings.access_secret_key, algorithm=settings.algorithm)
        return token, jti, expire
    except JWTError:
        return None


def create_refresh_token(data: dict[str, Any]) -> tuple[str, str, datetime] | None:
    """Create a JWT refresh token with the provided data. This function takes a dictionary of data as input, creates a copy of it, and adds an expiration time (based on the configured refresh token expiration days), a unique identifier (jti), and a type field set to "refresh". It then encodes this information into a JWT token using the configured secret key and algorithm. The function returns a tuple containing the generated token, the jti, and the expiration time. If there is an error during token creation, it returns None."""
    try:
        to_encode = data.copy()
        expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
        jti = str(uuid.uuid4())

        to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
        token = jwt.encode(to_encode, settings.refresh_secret_key, algorithm=settings.algorithm)
        return token, jti, expire
    except JWTError:
        return None


def verify_access_token(token: str) -> dict[str, Any] | None:
    """Verify the provided JWT access token. This function decodes the token using the configured secret key and algorithm, checks that the token type is "access", and returns the payload if the token is valid. If the token is invalid, expired, or of the wrong type, it returns None."""
    try:
        payload = jwt.decode(token, settings.access_secret_key, algorithms=[settings.algorithm])

        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def verify_refresh_token(token: str) -> dict[str, Any] | None:
    """Verify the provided JWT refresh token. This function decodes the token using the configured secret key and algorithm, checks that the token type is "refresh", and returns the payload if the token is valid. If the token is invalid, expired, or of the wrong type, it returns None."""
    try:
        payload = jwt.decode(token, settings.refresh_secret_key, algorithms=[settings.algorithm])

        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Retrieve the current user's information based on the JWT token payload. This function extracts the token payload from the request state, checks for the presence of user_id and email in the payload, and retrieves the corresponding user from the database. If the token is missing, invalid, or if the user cannot be found, it raises an appropriate exception (UnauthorizedException or NotFoundException). If successful, it returns a dictionary containing the user's id, name, email, and role."""
    payload = getattr(request.state, "user", None)

    if not payload:
        raise UnauthorizedException(detail="Unauthorized")

    user_id = payload.get("user_id")
    email = payload.get("sub")

    if not user_id or not email:
        raise UnauthorizedException(detail="Invalid token payload")

    user = await get_data_by_id(User, user_id, db)

    if not user:
        raise NotFoundException(detail="User not found")

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }
