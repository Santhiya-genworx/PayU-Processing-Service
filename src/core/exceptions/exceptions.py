from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base class for all application exceptions."""

    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundException(AppException):
    """Resource not found."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail, status.HTTP_404_NOT_FOUND)


class UnauthorizedException(AppException):
    """Authentication/authorization failure."""

    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(detail, status.HTTP_401_UNAUTHORIZED)


class ConflictException(AppException):
    """Conflict error, e.g., duplicate entry."""

    def __init__(self, detail: str = "Conflict"):
        super().__init__(detail, status.HTTP_409_CONFLICT)


class BadRequestException(AppException):
    """Bad request error, e.g., invalid input."""

    def __init__(self, detail: str = "Bad request"):
        super().__init__(detail, status.HTTP_400_BAD_REQUEST)
