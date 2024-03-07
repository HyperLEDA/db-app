from dataclasses import dataclass

from marshmallow import Schema, fields, post_load, validate


@dataclass
class CreateSourceRequest:
    type: str
    metadata: dict


class CreateSourceRequestSchema(Schema):
    type = fields.Str(
        required=True,
        validate=validate.OneOf(["publication", "catalog", "table"]),
        description="Source type",
    )
    metadata = fields.Dict()

    @post_load
    def make_request(self, data, **kwargs):
        return CreateSourceRequest(**data)


class CreateSourceResponseSchema(Schema):
    id = fields.Int(
        required=True,
        description="HyperLeda source id",
    )


@dataclass
class CreateSourceResponse:
    id: int
