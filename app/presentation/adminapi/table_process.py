from aiohttp import web
from marshmallow import Schema, ValidationError, fields

from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


class CrossIdentificationSchema(schema.RequestSchema):
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

    class Meta:
        model = interface.CrossIdentification


class TableProcessRequestSchema(schema.RequestSchema):
    table_id = fields.Integer(required=True, description="Identifier of the table")
    cross_identification = fields.Nested(
        CrossIdentificationSchema,
        allow_nan=True,
        description="Cross-identification parameters for the processing",
    )

    class Meta:
        model = interface.TableProcessRequest


class TableProcessResponseSchema(Schema):
    pass


async def table_process_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
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

    return responses.APIOkResponse(actions.table_process(request))
