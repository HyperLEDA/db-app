from aiohttp import web
from marshmallow import Schema, ValidationError, fields, validate

from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


class CreateSourceRequestSchema(schema.RequestSchema):
    title = fields.Str(required=True, description="Title of publication")
    authors = fields.List(fields.Str, required=True, description="List of authors")
    year = fields.Int(required=True, description="Year of the publication", validate=validate.Range(1500), example=2006)

    class Meta:
        model = interface.CreateSourceRequest


class CreateSourceResponseSchema(Schema):
    code = fields.Str(
        required=True,
        description="Code for the source",
    )


async def create_source_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
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

    return responses.APIOkResponse(actions.create_source(request))
