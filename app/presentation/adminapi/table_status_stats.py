from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import schema
from app.commands.adminapi import depot
from app.domain import adminapi
from app.lib.storage import enums
from app.lib.web import responses, server
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import common


class TableStatusStatsRequestSchema(Schema):
    table_id = fields.Integer(required=True, description="Identifier of the table")

    @post_load
    def make(self, data, **kwargs) -> schema.TableStatusStatsRequest:
        return schema.TableStatusStatsRequest(**data)


class TableStatusStatsResponseSchema(Schema):
    processing = fields.Dict(keys=fields.Enum(enums.ObjectProcessingStatus), values=fields.Integer())


async def table_status_stats(dpt: depot.Depot, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Get statistics on table processing
    description: |
        Accesses the current status of the processing of a given table.
        Returns the distribution of objects by processing status.

        If there are no objects with the given status, it will not be present in the response.
    security:
        - TokenAuth: []
    tags: [admin, table]
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

    return responses.APIOkResponse(adminapi.table_status_stats(dpt, request))


description = common.handler_description(
    server.HTTPMethod.GET,
    "/api/v1/table/status/stats",
    table_status_stats,
    TableStatusStatsRequestSchema,
    TableStatusStatsResponseSchema,
)
