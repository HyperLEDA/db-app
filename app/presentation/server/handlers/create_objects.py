from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error

ALLOWED_OBJECT_TYPES = ["galaxy", "star"]
ALLOWED_COORDINATE_SYSTEMS = ["equatorial"]
ALLOWED_EPOCHS = ["J2000"]


class CoordsInfoSchema(Schema):
    ra = fields.Float(
        required=True,
        description="Right ascension coordinate, degrees.",
        validate=validate.Range(0, 360),
    )
    dec = fields.Float(
        required=True,
        description="Declination coordinate, degrees.",
        validate=validate.Range(-90, 90),
    )

    @post_load
    def make(self, data, **kwargs) -> model.CoordsInfo:
        return model.CoordsInfo(**data)


class PositionInfoSchema(Schema):
    coordinate_system = fields.Str(
        required=True,
        description="Coordinate system name",
        validate=validate.OneOf(ALLOWED_COORDINATE_SYSTEMS),
    )
    epoch = fields.Str(
        required=True,
        description="Epoch of the coordinates",
        validate=validate.OneOf(ALLOWED_EPOCHS),
    )
    coords = fields.Nested(
        CoordsInfoSchema,
        required=True,
        description="Value of the coordinates",
    )

    @post_load
    def make(self, data, **kwargs) -> model.PositionInfo:
        return model.PositionInfo(**data)


class ObjectInfoSchema(Schema):
    name = fields.Str(required=True, description="Designation of an object")
    type = fields.Str(
        required=True,
        description="Type of an object",
        validate=validate.OneOf(ALLOWED_OBJECT_TYPES),
    )
    position = fields.Nested(
        PositionInfoSchema,
        required=True,
        description="Positional information of an object",
    )

    @post_load
    def make(self, data, **kwargs) -> model.ObjectInfo:
        return model.ObjectInfo(**data)


class CreateObjectBatchRequestSchema(Schema):
    source_id = fields.Int(
        required=True,
        description="ID of the source that provides objects",
    )
    objects = fields.List(
        fields.Nested(ObjectInfoSchema),
        required=True,
        description="List of objects",
    )

    @post_load
    def make(self, data, **kwargs) -> model.CreateObjectBatchRequest:
        return model.CreateObjectBatchRequest(**data)


class CreateObjectBatchResponseSchema(Schema):
    ids = fields.List(fields.Int(), description="List of ids of saved objects")


@docs(
    summary="Create batch of objects",
    tags=["objects"],
    description="Creates batch of objects assosiated with the source.",
)
@request_schema(CreateObjectBatchRequestSchema())
@response_schema(CreateObjectBatchResponseSchema(), 200)
async def create_objects_handler(actions: domain.Actions, r: web.Request) -> Any:
    request_dict = await r.json()
    try:
        request = CreateObjectBatchRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.create_objects(request)
