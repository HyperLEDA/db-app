from typing import Any

from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import common


class CreateSourceRequestSchema(Schema):
    bibcode = fields.Str(description="Bibcode of publication", example="2001quant.ph..1003R")
    title = fields.Str(description="Title of publication")
    authors = fields.List(fields.Str, description="List of authors")
    year = fields.Int(description="Year of the publication", validate=validate.Range(0))

    @post_load
    def make(self, data, **kwargs) -> model.CreateSourceRequest:
        return model.CreateSourceRequest(**data)


class CreateSourceResponseSchema(Schema):
    id = fields.Int(
        required=True,
        description="HyperLeda bibliography id",
    )


async def create_source_handler(actions: domain.Actions, r: web.Request) -> Any:
    """---
    summary: New bibliographic entry
    description: Creates new bibliographic entry in the database.
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
        raise new_validation_error(str(e)) from e

    return actions.create_source(request)


description = common.HandlerDescription(
    common.HTTPMethod.POST,
    "/api/v1/admin/source",
    create_source_handler,
    CreateSourceRequestSchema,
    CreateSourceResponseSchema,
)
