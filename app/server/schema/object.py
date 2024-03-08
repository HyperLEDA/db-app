from dataclasses import dataclass

from marshmallow import Schema, fields, post_load, validate

ALLOWED_COORDINATE_SYSTEMS = ["equatorial"]
ALLOWED_EPOCHS = ["J2000"]
ALLOWED_OBJECT_TYPES = ["galaxy", "star"]


@dataclass
class CoordsInfo:
    ra: float
    dec: float


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
    def make(self, data, **kwargs) -> CoordsInfo:
        return CoordsInfo(**data)


@dataclass
class PositionInfo:
    coordinate_system: str
    epoch: str
    coords: CoordsInfo


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
    def make(self, data, **kwargs) -> PositionInfo:
        return PositionInfo(**data)


@dataclass
class ObjectInfo:
    name: str
    type: str
    position: PositionInfo


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
    def make(self, data, **kwargs) -> ObjectInfo:
        return ObjectInfo(**data)


@dataclass
class CreateObjectBatchRequest:
    source_id: int
    objects: list[ObjectInfo]


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
    object: ObjectInfo


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


@dataclass
class GetObjectRequest:
    id: int


class GetObjectRequestSchema(Schema):
    id = fields.Int(
        required=True,
        description="ID of the object in HyperLeda database",
    )

    @post_load
    def make(self, data, **kwargs) -> GetObjectRequest:
        return GetObjectRequest(**data)


@dataclass
class GetObjectResponse:
    object: ObjectInfo


class GetObjectResponseSchema(Schema):
    object = fields.Nested(
        ObjectInfoSchema(),
        required=True,
        description="Description of the object",
    )


@dataclass
class SearchObjectsRequest:
    ra: float
    dec: float
    radius: float
    type: str
    page_size: int
    page: int


class SearchObjectsRequestSchema(Schema):
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
    radius = fields.Float(
        description="Search radius, arseconds",
        validate=validate.Range(0),
        load_default=10 * 60,
    )
    type = fields.Str(
        description="Type of an object",
        validate=validate.OneOf(ALLOWED_OBJECT_TYPES),
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
    def make(self, data, **kwargs) -> SearchObjectsRequest:
        return SearchObjectsRequest(**data)


@dataclass
class SearchObjectsResponse:
    objects: list[ObjectInfo]


class SearchObjectsResponseSchema(Schema):
    objects = fields.List(
        fields.Nested(ObjectInfoSchema()),
        required=True,
        description="List of objects that satisfy search filters",
    )
