from aiohttp import web
from marshmallow import Schema, ValidationError, fields

from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


class GetSourceRequestSchema(schema.RequestSchema):
    id = fields.Int(
        required=True,
        description="HyperLeda source id",
    )

    class Meta:
        model = interface.GetSourceRequest


class GetSourceResponseSchema(Schema):
    code = fields.Str(description="Bibcode or internal code of the publication")
    title = fields.Str(description="Title of publication")
    authors = fields.List(fields.Str, description="List of authors")
    year = fields.Int(description="Year of the publication")


async def get_source_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Get information about source
    description: Retrieves information about the source using its id
    tags: [source]
    parameters:
      - in: query
        schema: GetSourceRequestSchema
    responses:
        200:
            description: Source was successfully obtained
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: GetSourceResponseSchema
    """
    try:
        request = GetSourceRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.get_source(request))
