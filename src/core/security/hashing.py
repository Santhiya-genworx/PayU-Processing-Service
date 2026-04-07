"""Module for hashing and verifying data using the Argon2 algorithm. This module provides two main functions: hash_data and verify_data. The hash_data function takes a plain string as input and returns a securely hashed version of that string using the Argon2 algorithm, which is designed to be resistant to brute-force attacks and is considered one of the most secure hashing algorithms available. The verify_data function takes a plain string and a hashed string as input and verifies whether the plain string matches the hashed version, returning True if they match and False otherwise. This module is essential for securely handling sensitive information such as passwords or other confidential data in the PayU Processing Service application."""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_data(data: str) -> str:
    """Hash the provided data using the password context. This function takes a plain string as input and returns a securely hashed version of that string using the Argon2 algorithm. This is commonly used for hashing passwords or other sensitive information before storing it in a database, ensuring that the original data cannot be easily retrieved or compromised."""
    return pwd_context.hash(data)


def verify_data(plain_data: str, hashed_data: str) -> bool:
    """Verify that the provided plain data matches the hashed data. This function uses the password context to compare the plain data with the hashed version, returning True if they match and False otherwise. This is commonly used for verifying passwords or other sensitive information that has been securely hashed before storage."""
    return pwd_context.verify(plain_data, hashed_data)
