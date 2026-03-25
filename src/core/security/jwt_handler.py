import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, Request
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db
from src.core.config.settings import settings
from src.core.exceptions.exceptions import NotFoundException, UnauthorizedException
from src.data.models.user_model import User
from src.data.repositories.base_repository import get_data_by_id


def create_access_token(data: dict[str, Any]) -> tuple[str, str, datetime] | None:
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
    try:
        payload = jwt.decode(token, settings.access_secret_key, algorithms=[settings.algorithm])

        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def verify_refresh_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.refresh_secret_key, algorithms=[settings.algorithm])

        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
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
