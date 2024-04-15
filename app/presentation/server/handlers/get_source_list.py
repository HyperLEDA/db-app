from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import create_source, get_source


class GetSourceListRequestSchema(Schema):
    type = fields.Str(
        required=True,
        validate=validate.OneOf(create_source.ALLOWED_SOURCE_TYPES),
        description="Source type",
    )
    page_size = fields.Int(
        load_default=20,
        description="Number of entries in the page",
        validate=validate.OneOf([10, 20, 50, 100]),
    )
    page = fields.Int(
        load_default=0,
        description="Page number",
        validate=validate.Range(0),
    )

    @post_load
    def make(self, data, **kwargs) -> model.GetSourceListRequest:
        return model.GetSourceListRequest(**data)


class GetSourceListResponseSchema(Schema):
    sources = fields.List(fields.Nested(get_source.GetSourceResponseSchema()), description="List of sources")


@docs(
    summary="Obtain list of sources",
    tags=["sources"],
    description="Obtains a list of sources that satisfy given filters sorted by modification time.",
)
@querystring_schema(GetSourceListRequestSchema())
@response_schema(GetSourceListResponseSchema(), 200)
async def get_source_list_handler(actions: domain.Actions, r: web.Request) -> Any:
    try:
        request = GetSourceListRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.get_source_list(request)
