from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import schema
from app.commands.adminapi import depot
from app.domain import adminapi
from app.lib.web import responses, server
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import common


class GetSourceRequestSchema(Schema):
    id = fields.Int(
        required=True,
        description="HyperLeda source id",
    )

    @post_load
    def make(self, data, **kwargs) -> schema.GetSourceRequest:
        return schema.GetSourceRequest(**data)


class GetSourceResponseSchema(Schema):
    code = fields.Str(description="Bibcode or internal code of the publication")
    title = fields.Str(description="Title of publication")
    authors = fields.List(fields.Str, description="List of authors")
    year = fields.Int(description="Year of the publication")


async def get_source_handler(dpt: depot.Depot, r: web.Request) -> responses.APIOkResponse:
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

    return responses.APIOkResponse(adminapi.get_source(dpt, request))


description = common.handler_description(
    server.HTTPMethod.GET,
    "/api/v1/source",
    get_source_handler,
    GetSourceRequestSchema,
    GetSourceResponseSchema,
)
