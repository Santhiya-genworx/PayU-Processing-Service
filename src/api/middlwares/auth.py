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
        if request.url.path in public_urls:
            return await call_next(request)
        
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            token = request.cookies.get("access_token")
        else:
            return JSONResponse(status_code=401, content={"detail": "Authorization Header Missing"})

        try:
            payload = jwt.decode(token, settings.access_secret_key, algorithms = [settings.algorithm])
            request.state.user = payload
        except JWTError as err:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
        
        response = await call_next(request)
        return response