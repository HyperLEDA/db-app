from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error


class CreateSourceRequestSchema(Schema):
    bibcode = fields.Str(description="Bibcode of publication")
    title = fields.Str(description="Title of publication")
    authors = fields.List(fields.Str, description="List of authors")
    year = fields.Int(description="Year of the publication")

    @post_load
    def make(self, data, **kwargs) -> model.CreateSourceRequest:
        return model.CreateSourceRequest(**data)


class CreateSourceResponseSchema(Schema):
    id = fields.Int(
        required=True,
        description="HyperLeda bibliography id",
    )


@docs(
    summary="Create new source",
    tags=["sources"],
    description="Creates new source that can be referenced when adding new objects.",
)
@request_schema(CreateSourceRequestSchema())
@response_schema(CreateSourceResponseSchema(), 200)
async def create_source_handler(actions: domain.Actions, r: web.Request) -> Any:
    request_dict = await r.json()
    try:
        request = CreateSourceRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.create_source(request)
