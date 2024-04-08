from marshmallow import Schema, fields, post_load, validate

from app.domain import model

ALLOWED_COORDINATE_SYSTEMS = ["equatorial"]
ALLOWED_EPOCHS = ["J2000"]
ALLOWED_OBJECT_TYPES = ["galaxy", "star"]


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


class CreateObjectResponseSchema(Schema):
    id = fields.Int(
        required=True,
        description="ID of the object in HyperLeda database",
    )


class CreateObjectRequestSchema(Schema):
    source_id = fields.Int(
        required=True,
        description="ID of the source that provides objects",
    )
    object = fields.Nested(
        ObjectInfoSchema(),
        required=True,
        description="Description of the object",
    )

    @post_load
    def make(self, data, **kwargs) -> model.CreateObjectRequest:
        return model.CreateObjectRequest(**data)


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
    page = fields.Int(
        load_default=0,
        description="Page number",
        validate=validate.Range(0),
    )

    @post_load
    def make(self, data, **kwargs) -> model.GetObjectNamesRequest:
        return model.GetObjectNamesRequest(**data)


class ObjectNameInfoSchema(Schema):
    name = fields.Str(description="Designation of the object")
    source_id = fields.Str(description="ID of the source")
    modification_time = fields.DateTime(description="Last time this name was modified")


class GetObjectNamesResponseSchema(Schema):
    names = fields.Nested(ObjectNameInfoSchema, description="List of names and metadata about them")
