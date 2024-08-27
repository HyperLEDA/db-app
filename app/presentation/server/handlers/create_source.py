from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import commands
from app.domain import actions, model
from app.lib.web import responses
from app.lib.web.errors import RuleValidationError
from app.presentation.server.handlers import common


class CreateSourceRequestSchema(Schema):
    title = fields.Str(required=True, description="Title of publication")
    authors = fields.List(fields.Str, required=True, description="List of authors")
    year = fields.Int(required=True, description="Year of the publication", validate=validate.Range(1500))

    @post_load
    def make(self, data, **kwargs) -> model.CreateSourceRequest:
        return model.CreateSourceRequest(**data)


class CreateSourceResponseSchema(Schema):
    code = fields.Str(
        required=True,
        description="Code for the source",
    )


async def create_source_handler(depot: commands.Depot, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: New source entry
    description: Creates new source entry in the database for internal communication and unpublished articles.
    security:
        - TokenAuth: []
    tags: [admin, source]
    requestBody:
        content:
            application/json:
                schema: CreateSourceRequestSchema
    responses:
        200:
            description: Source was successfully created
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: CreateSourceResponseSchema
    """
    request_dict = await r.json()
    try:
        request = CreateSourceRequestSchema().load(request_dict)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.create_source(depot, request))


description = common.HandlerDescription(
    common.HTTPMethod.POST,
    "/api/v1/admin/source",
    create_source_handler,
    CreateSourceRequestSchema,
    CreateSourceResponseSchema,
)
