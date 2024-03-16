from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import ValidationError

from app import domain
from app.lib.exceptions import new_validation_error
from app.presentation.model import (
    GetObjectNamesRequestSchema,
    GetObjectNamesResponseSchema,
)


@docs(
    summary="Get information about the object designations",
    tags=["objects"],
    description="Retrieves information about the object names using its id.",
)
@querystring_schema(GetObjectNamesRequestSchema())
@response_schema(GetObjectNamesResponseSchema(), 200)
async def get_object_names(actions: domain.Actions, r: web.Request) -> Any:
    try:
        request = GetObjectNamesRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.get_object_names(request)
