from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema

from app import domain
from app.domain import model
from marshmallow import Schema, ValidationError, fields, post_load
from app.lib.exceptions import new_validation_error


class GetSourceRequestSchema(Schema):
    id = fields.Int(
        required=True,
        description="HyperLeda source id",
    )

    @post_load
    def make(self, data, **kwargs) -> model.GetSourceRequest:
        return model.GetSourceRequest(**data)


class GetSourceResponseSchema(Schema):
    bibcode = fields.Str(description="Bibcode of publication")
    title = fields.Str(description="Title of publication")
    authors = fields.List(fields.Str, description="List of authors")
    year = fields.Int(description="Year of the publication")


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
