from dataclasses import dataclass
from typing import Any

from marshmallow import Schema, fields, post_load, validate

ALLOWED_SOURCE_TYPES = ["publication", "catalog", "table"]


@dataclass
class CreateSourceRequest:
    type: str
    metadata: dict


class CreateSourceRequestSchema(Schema):
    type = fields.Str(
        required=True,
        validate=validate.OneOf(ALLOWED_SOURCE_TYPES),
        description="Source type",
    )
    metadata = fields.Dict()

    @post_load
    def make(self, data, **kwargs) -> CreateSourceRequest:
        return CreateSourceRequest(**data)


@dataclass
class CreateSourceResponse:
    id: int


class CreateSourceResponseSchema(Schema):
    id = fields.Int(
        required=True,
        description="HyperLeda source id",
    )


@dataclass
class GetSourceRequest:
    id: int


class GetSourceRequestSchema(Schema):
    id = fields.Int(
        required=True,
        description="HyperLeda source id",
    )

    @post_load
    def make(self, data, **kwargs) -> GetSourceRequest:
        return GetSourceRequest(**data)


@dataclass
class GetSourceResponse:
    type: str
    metadata: dict[str, Any]


class GetSourceResponseSchema(Schema):
    type = fields.Str(
        required=True,
        validate=validate.OneOf(ALLOWED_SOURCE_TYPES),
        description="Source type",
    )
    metadata = fields.Dict(
        description="Metadata that provides identification for the source",
    )


@dataclass
class GetSourceListRequest:
    type: str
    page_size: int
    page: int


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
    def make(self, data, **kwargs) -> GetSourceListRequest:
        return GetSourceListRequest(**data)


@dataclass
class GetSourceListResponse:
    sources: list[GetSourceResponse]


class GetSourceListResponseSchema(Schema):
    sources = fields.List(fields.Nested(GetSourceResponseSchema()), description="List of sources")
