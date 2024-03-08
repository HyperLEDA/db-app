from dataclasses import dataclass

from marshmallow import Schema, fields, post_load, validate


@dataclass
class CoordsRequest:
    ra: float
    dec: float


class CoordsRequestSchema(Schema):
    ra = fields.Float(
        required=True,
        description="Right ascension coordinate",
        validate=validate.Range(0, 360),
    )
    dec = fields.Float(
        required=True,
        description="Declination coordinate",
        validate=validate.Range(-90, 90),
    )

    @post_load
    def make(self, data, **kwargs) -> CoordsRequest:
        return CoordsRequest(**data)


@dataclass
class PositionRequest:
    coordinate_system: str
    epoch: str
    coords: CoordsRequest


class PositionRequestSchema(Schema):
    coordinate_system = fields.Str(
        required=True,
        description="Coordinate system name",
        validate=validate.OneOf(["equatorial"]),
    )
    epoch = fields.Str(
        required=True,
        description="Epoch of the coordinates",
        validate=validate.OneOf(["J2000"]),
    )
    coords = fields.Nested(
        CoordsRequestSchema,
        required=True,
        description="Value of the coordinates",
    )

    @post_load
    def make(self, data, **kwargs) -> PositionRequest:
        return PositionRequest(**data)


@dataclass
class ObjectRequest:
    name: str
    type: str
    position: PositionRequest


class ObjectRequestSchema(Schema):
    name = fields.Str(required=True, description="Designation of an object")
    type = fields.Str(
        required=True,
        description="Type of an object",
        validate=validate.OneOf(["galaxy", "star"]),
    )
    position = fields.Nested(
        PositionRequestSchema,
        required=True,
        description="Positional information of an object",
    )

    @post_load
    def make(self, data, **kwargs) -> ObjectRequest:
        return ObjectRequest(**data)


@dataclass
class CreateObjectBatchRequest:
    source_id: int
    objects: list[ObjectRequest]


class CreateObjectBatchRequestSchema(Schema):
    source_id = fields.Int(
        required=True,
        description="ID of the source that provides objects",
    )
    objects = fields.List(
        fields.Nested(ObjectRequestSchema),
        required=True,
        description="List of objects",
    )

    @post_load
    def make(self, data, **kwargs) -> CreateObjectBatchRequest:
        return CreateObjectBatchRequest(**data)


@dataclass
class CreateObjectBatchResponse:
    ids: list[int]


class CreateObjectBatchResponseSchema(Schema):
    ids = fields.List(fields.Int(), description="List of ids of saved objects")


@dataclass
class CreateObjectRequest:
    source_id: int
    object: ObjectRequest


class CreateObjectRequestSchema(Schema):
    source_id = fields.Int(
        required=True,
        description="ID of the source that provides objects",
    )
    object = fields.Nested(
        ObjectRequestSchema(),
        required=True,
        description="Description of the object",
    )

    @post_load
    def make(self, data, **kwargs) -> CreateObjectRequest:
        return CreateObjectRequest(**data)


@dataclass
class CreateObjectResponse:
    id: int


class CreateObjectResponseSchema(Schema):
    id = fields.Int(
        required=True,
        description="ID of the object in HyperLeda database",
    )
