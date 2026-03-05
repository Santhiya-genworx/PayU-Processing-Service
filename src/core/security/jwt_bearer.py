from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from src.core.config.settings import settings

class JWTBearer(HTTPBearer):
    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if not credentials:
            raise HTTPException(status_code=401, detail="Invalid authorization code.")
        
        if credentials.scheme != "Bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme.")
        
        try:
            payload = jwt.decode(credentials.credentials, settings.access_secret_key, algorithms=[settings.algorithm])
            if not payload:
                payload = jwt.decode(request.cookies.get("access_token"), settings.access_secret_key, algorithms=[settings.algorithm])
            return payload
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
