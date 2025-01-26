from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import schema
from app.commands.adminapi import depot
from app.domain import actions
from app.lib.web import responses, server
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import common


class CrossIdentificationSchema(Schema):
    inner_radius_arcsec = fields.Float(
        allow_nan=True,
        load_default=1.5,
        description="Inner radius for the cross-identification collision detection",
    )
    outer_radius_arcsec = fields.Float(
        allow_nan=True,
        load_default=3,
        description="Outer radius for the cross-identification collision detection",
    )

    @post_load
    def make(self, data, **kwargs) -> schema.CrossIdentification:
        return schema.CrossIdentification(**data)


class TableProcessRequestSchema(Schema):
    table_id = fields.Integer(required=True, description="Identifier of the table")
    cross_identification = fields.Nested(
        CrossIdentificationSchema,
        allow_nan=True,
        description="Cross-identification parameters for the processing",
    )

    @post_load
    def make(self, data, **kwargs) -> schema.TableProcessRequest:
        return schema.TableProcessRequest(**data)


class TableProcessResponseSchema(Schema):
    pass


async def table_process_handler(dpt: depot.Depot, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Start processing of the table
    description: |
        Starts different processing steps on the table: for example, homogenization and cross-identification.
    security:
        - TokenAuth: []
    tags: [admin, table]
    requestBody:
        content:
            application/json:
                schema: TableProcessRequestSchema
    responses:
        200:
            description: Processing successfully started
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: TableProcessResponseSchema
    """
    request_dict = await r.json()
    try:
        request = TableProcessRequestSchema().load(request_dict)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.table_process(dpt, request))


description = common.handler_description(
    server.HTTPMethod.POST,
    "/api/v1/admin/table/process",
    table_process_handler,
    TableProcessRequestSchema,
    TableProcessResponseSchema,
)
