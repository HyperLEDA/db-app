import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import ValidationError

from presentation import actions
from presentation.model import GetSourceListRequestSchema, GetSourceListResponseSchema
from presentation.server.exceptions import new_validation_error


@docs(
    summary="Obtain list of sources",
    tags=["sources"],
    description="Obtains a list of sources that satisfy given filters.",
)
@request_schema(GetSourceListRequestSchema(), location="query")
@response_schema(GetSourceListResponseSchema(), 200)
async def get_source_list(r: web.Request) -> dict[str, Any]:
    try:
        request = GetSourceListRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e))

    response = actions.get_source_list(request)

    return {"data": dataclasses.asdict(response)}
