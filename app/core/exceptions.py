from fastapi import HTTPException, status


class AppException(Exception):
    """Base class for all application exceptions"""


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found"):
        self.message = message
        super().__init__(message)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        self.message = message
        super().__init__(message)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden"):
        self.message = message
        super().__init__(message)


class ConflictException(AppException):
    def __init__(self, message: str = "Conflict"):
        self.message = message
        super().__init__(message)


class ValidationException(AppException):
    def __init__(self, message: str = "Invalid data"):
        self.message = message
        super().__init__(message)
