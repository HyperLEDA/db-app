from aiohttp import web
from marshmallow import Schema, ValidationError, fields

from app.lib.storage import enums
from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


class TableStatusStatsRequestSchema(schema.RequestSchema):
    table_id = fields.Integer(required=True, metadata={"description": "Identifier of the table"})

    class Meta:
        model = interface.TableStatusStatsRequest


class TableStatusStatsResponseSchema(Schema):
    processing = fields.Dict(keys=fields.Enum(enums.ObjectCrossmatchStatus), values=fields.Integer())


async def table_status_stats(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Get statistics on table processing
    description: |
        Accesses the current status of the processing of a given table.
        Returns the distribution of objects by processing status.

        If there are no objects with the given status, it will not be present in the response.
    security:
        - TokenAuth: []
    tags: [table]
    parameters:
      - in: query
        schema: TableStatusStatsRequestSchema
    responses:
        200:
            description: Number of objects in each status
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: TableStatusStatsResponseSchema
    """
    try:
        request = TableStatusStatsRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.table_status_stats(request))
