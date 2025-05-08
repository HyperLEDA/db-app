from aiohttp import web
from marshmallow import Schema, fields
from marshmallow_generic import GenericSchema

from app.lib.web import responses
from app.presentation.adminapi import interface


class GetTableValidationRequestSchema(GenericSchema[interface.GetTableValidationRequest]):
    table_name = fields.Str(required=True, metadata={"description": "Name of the table"})


class TableValidation(Schema):
    message = fields.Str(metadata={"description": "Error message"})
    validator = fields.Str(metadata={"description": "Type of the rule that was not satisfied"})


class GetTableValidationResponseSchema(Schema):
    validations = fields.List(fields.Nested(TableValidation), metadata={"description": "List of validation errors"})


async def get_table_validation_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Validate table schema
    description: |
        Validates the schema of the table, including column units and UCDs.

        Returns code 200 even if there are validation errors.
    tags: [table]
    parameters:
      - in: query
        schema: GetTableValidationRequestSchema
    responses:
        200:
            description: Table was successfully validated
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: GetTableValidationResponseSchema
    """

    raise NotImplementedError
