from typing import Any

from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import commands
from app.domain import actions, model
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import common


class LoginRequestSchema(Schema):
    username = fields.Str(required=True, description="Username")
    password = fields.Str(required=True, description="Password")

    @post_load
    def make(self, data, **kwargs) -> model.LoginRequest:
        return model.LoginRequest(**data)


class LoginResponseSchema(Schema):
    token = fields.Str(
        description="Token used to authenticate user in handlers that require a specific role to access",
    )


async def login_handler(depot: commands.Depot, r: web.Request) -> Any:
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
        raise new_validation_error(str(e)) from e

    return actions.login(depot, request)


description = common.HandlerDescription(
    method=common.HTTPMethod.POST,
    endpoint="/api/v1/login",
    handler=login_handler,
    request_schema=LoginRequestSchema,
    response_schema=LoginResponseSchema,
)
