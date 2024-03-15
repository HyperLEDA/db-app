import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import ValidationError

from app.presentation import actions
from app.presentation.model import GetSourceRequestSchema, GetSourceResponseSchema
from app.presentation.server.exceptions import new_validation_error


@docs(
    summary="Get information about source",
    tags=["sources"],
    description="Retrieves information about the source using its id.",
)
@querystring_schema(GetSourceRequestSchema())
@response_schema(GetSourceResponseSchema(), 200)
async def get_source(r: web.Request) -> dict[str, Any]:
    try:
        request = GetSourceRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e))

    response = actions.get_source(request)

    return {"data": dataclasses.asdict(response)}
