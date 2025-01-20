from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import commands, schema
from app.domain import actions
from app.lib.web import responses, server
from app.lib.web.errors import RuleValidationError
from app.presentation.server.handlers import common


class LoginRequestSchema(Schema):
    username = fields.Str(required=True, description="Username")
    password = fields.Str(required=True, description="Password")

    @post_load
    def make(self, data, **kwargs) -> schema.LoginRequest:
        return schema.LoginRequest(**data)


class LoginResponseSchema(Schema):
    token = fields.Str(
        description="Token used to authenticate user in handlers that require a specific role to access",
    )


async def login_handler(depot: commands.Depot, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Login user with username and password
    description: Gives user credentials for authentication in handlers
    tags: [authentication]
    requestBody:
        content:
            application/json:
                schema: LoginRequestSchema
    responses:
        200:
            description: User was successfully logged in
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: LoginResponseSchema
    """
    request_dict = await r.json()
    try:
        request = LoginRequestSchema().load(request_dict)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.login(depot, request))


description = common.handler_description(
    server.HTTPMethod.POST,
    "/api/v1/login",
    login_handler,
    LoginRequestSchema,
    LoginResponseSchema,
)
