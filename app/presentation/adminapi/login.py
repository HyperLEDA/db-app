from aiohttp import web
from marshmallow import Schema, ValidationError, fields

from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


class LoginRequestSchema(schema.RequestSchema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)

    class Meta:
        model = interface.LoginRequest


class LoginResponseSchema(Schema):
    token = fields.Str(
        metadata={
            "description": "Token used to authenticate user in handlers that require a specific role to access",
        },
    )


async def login_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
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

    return responses.APIOkResponse(actions.login(request))
