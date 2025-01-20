from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import commands, schema
from app.domain import actions
from app.lib.web import responses
from app.lib.web.errors import RuleValidationError
from app.presentation.server.handlers import common


class OverridesSchema(Schema):
    id = fields.UUID(required=True, description="Internal ID of the object in the original table")
    pgc = fields.Integer(description="Validated external ID of the object")

    @post_load
    def make(self, data, **kwargs) -> schema.SetTableStatusOverrides:
        return schema.SetTableStatusOverrides(**data)


class SetTableStatusRequestSchema(Schema):
    table_id = fields.Integer(required=True, description="Identifier of the table")
    overrides = fields.List(fields.Nested(OverridesSchema))

    @post_load
    def make(self, data, **kwargs) -> schema.SetTableStatusRequest:
        return schema.SetTableStatusRequest(**data)


class SetTableStatusResponseSchema(Schema):
    pass


async def set_table_status_handler(depot: commands.Depot, r: web.Request) -> responses.APIOkResponse:
    """---
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

    return responses.APIOkResponse(actions.set_table_status(depot, request))


description = common.handler_description(
    common.HTTPMethod.POST,
    "/api/v1/admin/table/status",
    set_table_status_handler,
    SetTableStatusRequestSchema,
    SetTableStatusResponseSchema,
    summary="Set status of the table",
    description="Set status of the table and its objects.",
)
