import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import ValidationError

from app import domain
from app.lib.exceptions import new_validation_error
from app.presentation import actions
from app.presentation.model import (
    GetSourceListRequestSchema,
    GetSourceListResponseSchema,
)


@docs(
    summary="Obtain list of sources",
    tags=["sources"],
    description="Obtains a list of sources that satisfy given filters.",
)
@querystring_schema(GetSourceListRequestSchema())
@response_schema(GetSourceListResponseSchema(), 200)
async def get_source_list(_: domain.Actions, r: web.Request) -> dict[str, Any]:
    try:
        request = GetSourceListRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e))

    response = actions.get_source_list(request)

    return {"data": dataclasses.asdict(response)}
