from aiohttp import web
from marshmallow import Schema, ValidationError, fields, validate

from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.dataapi import interface, model


class DelimitedListField(fields.List):
    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return value.split(",")
        except AttributeError as e:
            raise ValidationError(f"{attr} is not a delimited list it has a non string value {value}.") from e


class QuerySimpleRequestSchema(schema.RequestSchema):
    pgcs = DelimitedListField(fields.Integer(description="List of PGC numbers"))
    ra = fields.Float(description="Right ascension of the center of the search area in degrees")
    dec = fields.Float(description="Declination of the center of the search area in degrees")
    radius = fields.Float(description="Radius of the search area in degrees")
    name = fields.String(description="Name of the object")
    cz = fields.Float(description="Redshift value")
    cz_err_percent = fields.Float(description="Acceptable deviation of the redshift value in percent")
    page_size = fields.Integer(
        description="Number of objects per page",
        validate=validate.OneOf([10, 25, 50, 100]),
        load_default=25,
    )
    page = fields.Integer(description="Page number", load_default=0)

    class Meta:
        model = interface.QuerySimpleRequest


class QuerySimpleResponseSchema(Schema):
    objects = fields.List(fields.Nested(model.PGCObjectSchema))


async def query_simple_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Query data about objects
    description: |
        Obtains data about the objects according to the specified parameters.
        All of the conditions are combined with the logical AND operator.
        For example, if both coordinates and designation are specified, object must be in the specified area and have
        the specified designation.

        Note that the answer is paginated to improve performance.
    parameters:
      - in: query
        schema: QuerySimpleRequestSchema
    responses:
        200:
            description: Success
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: QuerySimpleResponseSchema
    """
    try:
        request = QuerySimpleRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.query_simple(request))
