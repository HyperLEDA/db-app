from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import ValidationError

from app import domain
from app.lib.exceptions import new_validation_error
from app.presentation.model import (
    CreateObjectBatchRequestSchema,
    CreateObjectBatchResponseSchema,
)


@docs(
    summary="Create batch of objects",
    tags=["objects"],
    description="Creates batch of objects assosiated with the source.",
)
@request_schema(CreateObjectBatchRequestSchema())
@response_schema(CreateObjectBatchResponseSchema(), 200)
async def create_objects(actions: domain.Actions, r: web.Request) -> dict[str, Any]:
    request_dict = await r.json()
    try:
        request = CreateObjectBatchRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.create_objects(request)
