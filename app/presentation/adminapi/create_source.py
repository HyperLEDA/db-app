from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import schema
from app.commands.adminapi import depot
from app.domain import actions
from app.lib.web import responses, server
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import common


class CreateSourceRequestSchema(Schema):
    title = fields.Str(required=True, description="Title of publication")
    authors = fields.List(fields.Str, required=True, description="List of authors")
    year = fields.Int(required=True, description="Year of the publication", validate=validate.Range(1500), example=2006)

    @post_load
    def make(self, data, **kwargs) -> schema.CreateSourceRequest:
        return schema.CreateSourceRequest(**data)


class CreateSourceResponseSchema(Schema):
    code = fields.Str(
        required=True,
        description="Code for the source",
    )


async def create_source_handler(dpt: depot.Depot, r: web.Request) -> responses.APIOkResponse:
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

    return responses.APIOkResponse(actions.create_source(dpt, request))


description = common.handler_description(
    server.HTTPMethod.POST,
    "/api/v1/admin/source",
    create_source_handler,
    CreateSourceRequestSchema,
    CreateSourceResponseSchema,
)
