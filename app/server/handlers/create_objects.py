import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import ValidationError

from app import actions
from app.server.exceptions.apiexception import new_validation_error
from app.server.schema.object import (
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
async def create_objects(r: web.Request) -> dict[str, Any]:
    request_dict = await r.json()
    try:
        request = CreateObjectBatchRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e))

    response = actions.create_objects(request)

    return {"data": dataclasses.asdict(response)}
