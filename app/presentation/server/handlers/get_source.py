from typing import Any

from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import common


class GetSourceRequestSchema(Schema):
    id = fields.Int(
        required=True,
        description="HyperLeda source id",
    )

    @post_load
    def make(self, data, **kwargs) -> model.GetSourceRequest:
        return model.GetSourceRequest(**data)


class GetSourceResponseSchema(Schema):
    bibcode = fields.Str(description="Bibcode of publication")
    title = fields.Str(description="Title of publication")
    authors = fields.List(fields.Str, description="List of authors")
    year = fields.Int(description="Year of the publication")


async def get_source_handler(actions: domain.Actions, r: web.Request) -> Any:
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
        raise new_validation_error(str(e)) from e

    return actions.get_source(request)


description = common.HandlerDescription(
    common.HTTPMethod.GET,
    "/api/v1/source",
    get_source_handler,
    GetSourceRequestSchema,
    GetSourceResponseSchema,
)
