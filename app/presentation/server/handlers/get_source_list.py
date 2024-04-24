from typing import Any

from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import common, get_source


class GetSourceListRequestSchema(Schema):
    title = fields.Str(
        required=True,
        description="Filter for the title",
    )
    page_size = fields.Int(
        load_default=20,
        description="Number of entries in the page",
        validate=validate.OneOf([10, 20, 50, 100]),
    )
    page = fields.Int(
        load_default=0,
        description="Page number",
        validate=validate.Range(0),
    )

    @post_load
    def make(self, data, **kwargs) -> model.GetSourceListRequest:
        return model.GetSourceListRequest(**data)


class GetSourceListResponseSchema(Schema):
    sources = fields.List(fields.Nested(get_source.GetSourceResponseSchema()), description="List of sources")


async def get_source_list_handler(actions: domain.Actions, r: web.Request) -> Any:
    """---
    summary: Obtain list of sources
    description: Obtains a list of sources that satisfy given filters sorted by modification time.
    tags: [source]
    parameters:
      - in: query
        schema: GetSourceListRequestSchema
    responses:
        200:
            description: Source was successfully obtained
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: GetSourceListResponseSchema
    """
    try:
        request = GetSourceListRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.get_source_list(request)


description = common.HandlerDescription(
    common.HTTPMethod.GET,
    "/api/v1/source/list",
    get_source_list_handler,
    GetSourceListRequestSchema,
    GetSourceListResponseSchema,
)
