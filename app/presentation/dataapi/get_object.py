from marshmallow import Schema, fields

from app.presentation.dataapi import model


class GetObjectRequestSchema(Schema):
    pgc = fields.Integer()


class GetObjectResponseSchema(Schema):
    object = fields.Nested(model.PGCObjectSchema)
