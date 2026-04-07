"""
Authentication middleware for the PayU Processing Service API.
This module defines the AuthMiddleware class, which is responsible for validating JWT tokens in incoming requests. It checks for the presence of a token in the Authorization header or cookies, decodes the token, and attaches the user information to the request state for use in downstream route handlers.
If the token is missing, invalid, or expired, the middleware returns a 401 Unauthorized response"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import settings

"""Authentication middleware for the PayU Processing Service API.
This module defines the AuthMiddleware class, which is responsible for validating JWT tokens in incoming requests. It checks for the presence of a token in the Authorization header or cookies, decodes the token, and attaches the user information to the request state for use in downstream route handlers.
If the token is missing, invalid, or expired, the middleware returns a 401 Unauthorized response
"""


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to authenticate requests using JWT tokens.
    This middleware checks for a JWT token in the Authorization header or cookies, validates it, and attaches the user information to the request state. If authentication fails, it returns a 401 response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:

        public_urls = ["/", "/docs", "/openapi.json", "/users/login", "/users/create"]

        if request.url.path in public_urls:
            return await call_next(request)

        token: str | None = None

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            token = request.cookies.get("access_token")

        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication token missing"},
            )

        try:
            payload = jwt.decode(
                token,
                settings.access_secret_key,
                algorithms=[settings.algorithm],
            )
            request.state.user = payload

        except JWTError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        return await call_next(request)
