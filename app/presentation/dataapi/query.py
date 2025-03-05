from aiohttp import web
from marshmallow import Schema, ValidationError, fields

from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.dataapi import interface, model


class QueryRequestSchema(schema.RequestSchema):
    q = fields.String(description="Query string")

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
