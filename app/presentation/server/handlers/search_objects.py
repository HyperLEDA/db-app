import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import ValidationError

from app import domain
from app.lib.exceptions import new_validation_error
from app.presentation import actions
from app.presentation.model import (
    SearchObjectsRequestSchema,
    SearchObjectsResponseSchema,
)


@docs(
    summary="Search objects using filters",
    tags=["objects"],
    description="Retrieves information about the objects that satisfy given filters.",
)
@querystring_schema(SearchObjectsRequestSchema())
@response_schema(SearchObjectsResponseSchema(), 200)
async def search_objects(_: domain.Actions, r: web.Request) -> dict[str, Any]:
    try:
        request = SearchObjectsRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    response = actions.search_objects(request)

    return {"data": dataclasses.asdict(response)}
