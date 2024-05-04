import dataclasses
from dataclasses import dataclass
from http.client import FORBIDDEN

INTERNAL_ERROR_CODE = "internal_error"
VALIDATION_ERROR_CODE = "validation_error"
NOT_FOUND_ERROR = "not_found"
DATABASE_ERROR = "database_error"
UNAUTHORIZED_ERROR = "unauthorized"
FORBIDDEN_ERROR = "forbidden"


@dataclass
class APIException(Exception):
    code: str
    status: int
    message: str

    def __str__(self) -> str:
        return f"{self.code} (code {self.status}): {self.message}"

    def dict(self) -> dict:
        return dataclasses.asdict(self)


def new_internal_error(error: str | Exception) -> APIException:
    return APIException(INTERNAL_ERROR_CODE, 500, str(error))


def new_validation_error(error: str) -> APIException:
    return APIException(VALIDATION_ERROR_CODE, 400, error)


def new_not_found_error(error: str) -> APIException:
    return APIException(NOT_FOUND_ERROR, 404, error)


def new_database_error(error: str) -> APIException:
    return APIException(DATABASE_ERROR, 500, error)


def new_unauthorized_error(error: str) -> APIException:
    return APIException(UNAUTHORIZED_ERROR, 401, error)


def new_forbidden_error(error: str) -> APIException:
    return APIException(FORBIDDEN_ERROR, 403, error)
