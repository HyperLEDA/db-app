from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import create_source


class GetSourceRequestSchema(Schema):
    id = fields.Int(
        required=True,
        description="HyperLeda source id",
    )

    @post_load
    def make(self, data, **kwargs) -> model.GetSourceRequest:
        return model.GetSourceRequest(**data)


class GetSourceResponseSchema(Schema):
    type = fields.Str(
        required=True,
        validate=validate.OneOf(create_source.ALLOWED_SOURCE_TYPES),
        description="Source type",
    )
    metadata = fields.Dict(
        description="Metadata that provides identification for the source",
    )


@docs(
    summary="Get information about source",
    tags=["sources"],
    description="Retrieves information about the source using its id.",
)
@querystring_schema(GetSourceRequestSchema())
@response_schema(GetSourceResponseSchema(), 200)
async def get_source_handler(actions: domain.Actions, r: web.Request) -> Any:
    try:
        request = GetSourceRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.get_source(request)
