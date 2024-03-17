from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import ValidationError

from app import domain
from app.lib.exceptions import new_validation_error
from app.presentation.model import CreateSourceRequestSchema, CreateSourceResponseSchema


@docs(
    summary="Create new source",
    tags=["sources"],
    description="Creates new source that can be referenced when adding new objects.",
)
@request_schema(CreateSourceRequestSchema())
@response_schema(CreateSourceResponseSchema(), 200)
async def create_source(actions: domain.Actions, r: web.Request) -> Any:
    request_dict = await r.json()
    try:
        request = CreateSourceRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.create_source(request)
