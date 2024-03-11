import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import ValidationError

from presentation import actions
from presentation.model import SearchObjectsRequestSchema, SearchObjectsResponseSchema
from presentation.server.exceptions.apiexception import new_validation_error


@docs(
    summary="Search objects using filters",
    tags=["objects"],
    description="Retrieves information about the objects that satisfy given filters.",
)
@request_schema(SearchObjectsRequestSchema(), location="query")
@response_schema(SearchObjectsResponseSchema(), 200)
async def search_objects(r: web.Request) -> dict[str, Any]:
    try:
        request = SearchObjectsRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e))

    response = actions.search_objects(request)

    return {"data": dataclasses.asdict(response)}
