import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import ValidationError

from app import domain
from app.domain.model.pipeline import SearchCatalogsRequest
from app.lib.exceptions import new_validation_error
from app.presentation.model import (
    SearchCatalogsRequestSchema,
    SearchCatalogsResponseSchema,
)


@docs(
    summary="Obtain list of catalogs",
    tags=["pipeline"],
    description="Obtains a list of catalogs according to query.",
)
@querystring_schema(
    SearchCatalogsRequestSchema(),
    example=dataclasses.asdict(SearchCatalogsRequest("dss", 10)),
)
@response_schema(SearchCatalogsResponseSchema(), 200)
async def search_catalogs(actions: domain.Actions, r: web.Request) -> Any:
    try:
        request = SearchCatalogsRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.search_catalogs(request)
