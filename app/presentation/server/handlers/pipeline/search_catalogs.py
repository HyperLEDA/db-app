from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import ValidationError

from app import domain
from app.lib.exceptions import new_validation_error
from app.presentation.model import SearchCatalogsRequest, SearchCatalogsResponse


@docs(
    summary="Obtain list of catalogs",
    tags=["pipeline"],
    description="Obtains a list of catalogs according to query.",
)
@querystring_schema(SearchCatalogsRequest())
@response_schema(SearchCatalogsResponse(), 200)
async def search_catalogs(actions: domain.Actions, r: web.Request) -> Any:
    try:
        request = SearchCatalogsRequest().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.search_catalogs(request)
