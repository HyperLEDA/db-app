from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import commands, schema
from app.domain import actions
from app.lib.storage import enums
from app.lib.web import responses
from app.lib.web.errors import RuleValidationError
from app.presentation.server.handlers import common


class TableStatusStatsRequestSchema(Schema):
    table_id = fields.Integer(required=True, description="Identifier of the table")

    @post_load
    def make(self, data, **kwargs) -> schema.TableStatusStatsRequest:
        return schema.TableStatusStatsRequest(**data)


class TableStatusStatsResponseSchema(Schema):
    processing = fields.Dict(keys=fields.Enum(enums.ObjectProcessingStatus), values=fields.Integer())


async def table_status_stats(depot: commands.Depot, r: web.Request) -> responses.APIOkResponse:
    """---
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

    return responses.APIOkResponse(actions.table_status_stats(depot, request))


description = common.handler_description(
    common.HTTPMethod.GET,
    "/api/v1/table/status/stats",
    table_status_stats,
    TableStatusStatsRequestSchema,
    TableStatusStatsResponseSchema,
    summary="Get statistics on table processing",
    description="""
        Accesses the current status of the processing of a given table.
        Returns the distribution of objects by processing status.

        If there are no objects with the given status, it will not be present in the response.""",
)
