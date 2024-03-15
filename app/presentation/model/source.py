from marshmallow import Schema, fields, post_load, validate

from app.domain import model

ALLOWED_SOURCE_TYPES = ["publication", "catalog", "table"]


class CreateSourceRequestSchema(Schema):
    type = fields.Str(
        required=True,
        validate=validate.OneOf(ALLOWED_SOURCE_TYPES),
        description="Source type",
    )
    metadata = fields.Dict()

    @post_load
    def make(self, data, **kwargs) -> model.CreateSourceRequest:
        return model.CreateSourceRequest(**data)


class CreateSourceResponseSchema(Schema):
    id = fields.Int(
        required=True,
        description="HyperLeda source id",
    )


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
        validate=validate.OneOf(ALLOWED_SOURCE_TYPES),
        description="Source type",
    )
    metadata = fields.Dict(
        description="Metadata that provides identification for the source",
    )


class GetSourceListRequestSchema(Schema):
    type = fields.Str(
        required=True,
        validate=validate.OneOf(ALLOWED_SOURCE_TYPES),
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
    sources = fields.List(fields.Nested(GetSourceResponseSchema()), description="List of sources")
