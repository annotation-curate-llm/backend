class AppException(Exception):
    """Base class for all application exceptions"""


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found"):
        self.message = message


class ConflictError(AppException):
    def __init__(self, message: str = "Conflict"):
        self.message = message


class PermissionDeniedError(AppException):
    def __init__(self, message: str = "Permission denied"):
        self.message = message


class ValidationError(AppException):
    def __init__(self, message: str = "Invalid data"):
        self.message = message
