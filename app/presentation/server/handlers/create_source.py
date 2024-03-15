import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import ValidationError

from app.presentation import actions
from app.presentation.model import CreateSourceRequestSchema, CreateSourceResponseSchema
from app.presentation.server.exceptions.apiexception import new_validation_error


@docs(
    summary="Create new source",
    tags=["sources"],
    description="Creates new source that can be referenced when adding new objects.",
)
@request_schema(CreateSourceRequestSchema())
@response_schema(CreateSourceResponseSchema(), 200)
async def create_source(r: web.Request) -> dict[str, Any]:
    request_dict = await r.json()
    try:
        request = CreateSourceRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e))

    response = actions.create_source(request)

    return {"data": dataclasses.asdict(response)}
