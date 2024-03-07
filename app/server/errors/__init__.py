from dataclasses import dataclass

INTERNAL_ERROR_CODE = "internal_error"
VALIDATION_ERROR_CODE = "validation_error"


@dataclass
class APIError(Exception):
    code: str
    message: str


def new_internal_error(error: str | Exception) -> APIError:
    return APIError(INTERNAL_ERROR_CODE, str(error))


def new_validation_error(error: str) -> APIError:
    return APIError(VALIDATION_ERROR_CODE, error)
