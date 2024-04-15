from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import Schema, ValidationError, fields, post_load

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import create_objects


class CreateObjectRequestSchema(Schema):
    source_id = fields.Int(
        required=True,
        description="ID of the source that provides objects",
    )
    object = fields.Nested(
        create_objects.ObjectInfoSchema(),
        required=True,
        description="Description of the object",
    )

    @post_load
    def make(self, data, **kwargs) -> model.CreateObjectRequest:
        return model.CreateObjectRequest(**data)


class CreateObjectResponseSchema(Schema):
    id = fields.Int(
        required=True,
        description="ID of the object in HyperLeda database",
    )


@docs(
    summary="Create a single object",
    tags=["objects"],
    description="Creates an object assosiated with the source.",
)
@request_schema(CreateObjectRequestSchema())
@response_schema(CreateObjectResponseSchema(), 200)
async def create_object_handler(actions: domain.Actions, r: web.Request) -> Any:
    request_dict = await r.json()
    try:
        request = CreateObjectRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.create_object(request)
