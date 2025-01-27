from aiohttp import web
from marshmallow import Schema, ValidationError, fields

from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


class OverridesSchema(schema.RequestSchema):
    id = fields.UUID(required=True, description="Internal ID of the object in the original table")
    pgc = fields.Integer(description="Validated external ID of the object")

    class Meta:
        model = interface.SetTableStatusOverrides


class SetTableStatusRequestSchema(Schema):
    table_id = fields.Integer(required=True, description="Identifier of the table")
    overrides = fields.List(fields.Nested(OverridesSchema))

    class Meta:
        model = interface.SetTableStatusRequest


class SetTableStatusResponseSchema(Schema):
    pass


async def set_table_status_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Set status of the table
    description: |
        Set status of the table and its objects.
    security:
        - TokenAuth: []
    tags: [admin, table]
    requestBody:
        content:
            application/json:
                schema: SetTableStatusRequestSchema
    responses:
        200:
            description: Status successfully set
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: SetTableStatusResponseSchema
    """
    request_dict = await r.json()
    try:
        request = SetTableStatusRequestSchema().load(request_dict)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.set_table_status(request))
