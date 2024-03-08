from dataclasses import dataclass

from marshmallow import Schema, fields

INTERNAL_ERROR_CODE = "internal_error"
VALIDATION_ERROR_CODE = "validation_error"
NOT_FOUND_ERROR = "not_found"


@dataclass
class APIException(Exception):
    code: str
    message: str


def new_internal_error(error: str | Exception) -> APIException:
    return APIException(INTERNAL_ERROR_CODE, str(error))


def new_validation_error(error: str) -> APIException:
    return APIException(VALIDATION_ERROR_CODE, error)


def new_not_found_error(error: str) -> APIException:
    return APIException(NOT_FOUND_ERROR, error)
