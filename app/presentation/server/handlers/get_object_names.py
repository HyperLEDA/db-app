from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error


class ObjectNameInfoSchema(Schema):
    name = fields.Str(description="Designation of the object")
    source_id = fields.Str(description="ID of the source")
    modification_time = fields.DateTime(description="Last time this name was modified")


class GetObjectNamesRequestSchema(Schema):
    id = fields.Int(
        required=True,
        description="ID of the object in HyperLeda database",
    )
    page_size = fields.Int(
        load_default=20,
        description="Number of entries in the page",
        validate=validate.OneOf([10, 20, 50, 100]),
    )
    page = fields.Int(load_default=0, description="Page number", validate=validate.Range(0))

    @post_load
    def make(self, data, **kwargs) -> model.GetObjectNamesRequest:
        return model.GetObjectNamesRequest(**data)


class GetObjectNamesResponseSchema(Schema):
    names = fields.Nested(ObjectNameInfoSchema, description="List of names and metadata about them")


@docs(
    summary="Get information about the object designations",
    tags=["objects"],
    description="Retrieves information about the object names using its id.",
)
@querystring_schema(GetObjectNamesRequestSchema())
@response_schema(GetObjectNamesResponseSchema(), 200)
async def get_object_names_handler(actions: domain.Actions, r: web.Request) -> Any:
    try:
        request = GetObjectNamesRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.get_object_names(request)
