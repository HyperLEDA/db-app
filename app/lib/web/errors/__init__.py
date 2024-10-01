import abc

INTERNAL_ERROR_CODE = "internal_error"
LOGICAL_ERROR_CODE = "logical_error"
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
    """
    Internal error that shows some temporary problem. Allows retries.
    """

    def __init__(self, message: str | Exception):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (INTERNAL_ERROR_CODE, 500, str(self.msg))


class LogicalError(APIError):
    """
    Internal error that shows that something on the backend was logically wrong.
    For example, integrity of internal database or some invariant was broken.
    Usually indicates some bug in the code.
    """

    def __init__(self, message: str | Exception):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (LOGICAL_ERROR_CODE, 500, str(self.msg))


class RuleValidationError(APIError):
    """
    Some validation requirements of the request were not satisfied.
    """

    def __init__(self, message: str):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (VALIDATION_ERROR_CODE, 400, self.msg)


class NotFoundError(APIError):
    """
    Entity was not found.
    """

    def __init__(self, message: str):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (NOT_FOUND_ERROR, 404, self.msg)


class DatabaseError(APIError):
    """
    Internal error that originated in the database.
    """

    def __init__(self, message: str):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (DATABASE_ERROR, 500, self.msg)


class UnauthorizedError(APIError):
    """
    Client tried to obtain resource that requires authorization.
    """

    def __init__(self, message: str):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (UNAUTHORIZED_ERROR, 401, self.msg)


class ForbiddenError(APIError):
    """
    Client was authorized but did not have sufficient permissions to obtain resource.
    """

    def __init__(self, message: str):
        self.msg = message

    def data(self) -> tuple[str, int, str]:
        return (FORBIDDEN_ERROR, 403, self.msg)
