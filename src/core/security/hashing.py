from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_data(data: str) -> str:
    return pwd_context.hash(data)


def verify_data(plain_data: str, hashed_data: str) -> bool:
    return pwd_context.verify(plain_data, hashed_data)
