from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import ValidationError

from app import domain
from app.lib.exceptions import new_validation_error
from app.presentation.model import GetSourceRequestSchema, GetSourceResponseSchema


@docs(
    summary="Get information about source",
    tags=["sources"],
    description="Retrieves information about the source using its id.",
)
@querystring_schema(GetSourceRequestSchema())
@response_schema(GetSourceResponseSchema(), 200)
async def get_source(actions: domain.Actions, r: web.Request) -> Any:
    try:
        request = GetSourceRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.get_source(request)
