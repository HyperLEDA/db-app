from marshmallow import Schema, fields, validate


class CreateSourceRequestSchema(Schema):
    type = fields.Str(required=True, validate=validate.OneOf(["publication", "catalog", "table"]))
    metadata = fields.Dict()
