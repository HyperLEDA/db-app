from aiohttp import web
from marshmallow import Schema, ValidationError, fields, validate
from marshmallow_generic import GenericSchema

from app.lib.web import responses
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


class CreateSourceRequestSchema(GenericSchema[interface.CreateSourceRequest]):
    title = fields.Str(
        required=True,
        metadata={"description": "Title of publication"},
    )
    authors = fields.List(
        fields.Str,
        required=True,
        metadata={"description": "List of authors"},
    )
    year = fields.Int(
        required=True,
        metadata={"description": "Year of the publication", "example": 2006},
        validate=validate.Range(1500),
    )


class CreateSourceResponseSchema(Schema):
    code = fields.Str(
        required=True,
        metadata={"description": "Code for the source"},
    )


async def create_source_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: New source entry
    description: Creates new source entry in the database for internal communication and unpublished articles.
    security:
        - TokenAuth: []
    tags: [source]
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
