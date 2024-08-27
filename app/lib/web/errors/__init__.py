import abc

INTERNAL_ERROR_CODE = "internal_error"
VALIDATION_ERROR_CODE = "validation_error"
NOT_FOUND_ERROR = "not_found"
DATABASE_ERROR = "database_error"
UNAUTHORIZED_ERROR = "unauthorized"
FORBIDDEN_ERROR = "forbidden"


class APIError(abc.ABC, Exception):
    def dict(self) -> dict:
        code, status, msg = self.data()
        return {
            "code": code,
            "status": status,
            "message": msg,
        }

    def status(self) -> int:
        _, status, _ = self.data()
        return status

    def message(self) -> str:
        _, _, msg = self.data()
        return msg

    @abc.abstractmethod
    def data(self) -> tuple[str, int, str]:
        pass


class InternalError(APIError):
    def __init__(self, message: str | Exception):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (INTERNAL_ERROR_CODE, 500, str(self.msg))


class RuleValidationError(APIError):
    def __init__(self, message: str):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (VALIDATION_ERROR_CODE, 400, self.msg)


class NotFoundError(APIError):
    def __init__(self, message: str):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (NOT_FOUND_ERROR, 404, self.msg)


class DatabaseError(APIError):
    def __init__(self, message: str):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (DATABASE_ERROR, 500, self.msg)


class UnauthorizedError(APIError):
    def __init__(self, message: str):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (UNAUTHORIZED_ERROR, 401, self.msg)


class ForbiddenError(APIError):
    def __init__(self, message: str):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (FORBIDDEN_ERROR, 403, self.msg)
