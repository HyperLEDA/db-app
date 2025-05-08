from aiohttp import web
from marshmallow import Schema, ValidationError, fields, validate

from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.dataapi import interface, model


class QueryRequestSchema(schema.RequestSchema):
    q = fields.String(metadata={"description": "Query string"})
    page_size = fields.Integer(
        metadata={"description": "Number of objects per page"},
        validate=validate.OneOf([10, 25, 50, 100]),
        load_default=25,
    )
    page = fields.Integer(metadata={"description": "Page number"}, load_default=0)

    class Meta:
        model = interface.QueryRequest


class QueryResponseSchema(Schema):
    objects = fields.List(fields.Nested(model.PGCObjectSchema))


async def query_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Query data about objects using query string
    description: |
        Obtains objects using the query string. It is composed of functions and operators.

        Allowed functions are:
        - `pgc`: Returns object with the particular PGC number.
        - `name`: Returns objects that are sufficiently similar to the given name.
        - `pos`: Returns objects that are within 1 arcsecond to the given coordinates.

        Allowed operators are:
        - `and`: Logical AND operator.
        - `or`: Logical OR operator.

        Note that the answer is paginated to improve performance.
    parameters:
      - in: query
        schema: QueryRequestSchema
    responses:
        200:
            description: Success
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: QueryResponseSchema
    """
    try:
        request = QueryRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.query(request))
