from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import ValidationError

from app import domain
from app.lib.exceptions import new_validation_error
from app.presentation.model import CreateObjectRequestSchema, CreateObjectResponseSchema


@docs(
    summary="Create a single object",
    tags=["objects"],
    description="Creates an object assosiated with the source.",
)
@request_schema(CreateObjectRequestSchema())
@response_schema(CreateObjectResponseSchema(), 200)
async def create_object(actions: domain.Actions, r: web.Request) -> dict[str, Any]:
    request_dict = await r.json()
    try:
        request = CreateObjectRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.create_object(request)
