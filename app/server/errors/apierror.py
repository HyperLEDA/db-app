from dataclasses import dataclass

from marshmallow import Schema, fields

INTERNAL_ERROR_CODE = "internal_error"
VALIDATION_ERROR_CODE = "validation_error"
NOT_FOUND_ERROR = "not_found"


class APIError(Schema, Exception):
    code = fields.Str(required=True)
    message = fields.Str(required=True)


def new_api_error(code: str, message: str) -> APIError:
    return APIError().load({"code": code, "message": message})


def new_internal_error(error: str | Exception) -> APIError:
    return new_api_error(INTERNAL_ERROR_CODE, str(error))


def new_validation_error(error: str) -> APIError:
    return new_api_error(VALIDATION_ERROR_CODE, error)


def new_not_found_error(error: str) -> APIError:
    return new_api_error(NOT_FOUND_ERROR, error)
