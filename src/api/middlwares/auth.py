from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from src.core.config.settings import settings

class AuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        public_urls = [
            "/",
            "/docs",
            "/openapi.json",
            "/users/login",
            "/users/create"
        ]

        # ✅ Allow public routes
        if request.url.path in public_urls:
            return await call_next(request)

        token = None

        # ✅ 1. Check Authorization header FIRST
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        # ✅ 2. If not in header, check cookies
        if not token:
            token = request.cookies.get("access_token")

        # ❌ If still no token → reject
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication token missing"}
            )

        # ✅ Decode safely
        try:
            payload = jwt.decode(
                token,
                settings.access_secret_key,
                algorithms=[settings.algorithm]
            )
            request.state.user = payload

        except JWTError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"}
            )

        return await call_next(request)