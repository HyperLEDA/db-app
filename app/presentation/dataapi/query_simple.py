from aiohttp import web
from marshmallow import Schema, ValidationError, fields, validate

from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.dataapi import interface, model


class QuerySimpleRequestSchema(schema.RequestSchema):
    ra = fields.Float(description="Right ascension of the center of the search area in degrees")
    dec = fields.Float(description="Declination of the center of the search area in degrees")
    radius = fields.Float(description="Radius of the search area in arcseconds")
    name = fields.String(description="Name of the object")
    designation = fields.String(description="Designation of the object")
    page_size = fields.Integer(
        required=True,
        description="Number of objects per page",
        validate=validate.OneOf([10, 25, 50, 100]),
    )
    page = fields.Integer(required=True, description="Page number")

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
    security:
        - TokenAuth: []
    requestBody:
        content:
            application/json:
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
