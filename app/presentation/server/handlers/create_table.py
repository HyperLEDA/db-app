from functools import wraps
from typing import Any, TypeVar

from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import commands
from app.domain import actions, model
from app.lib.storage import enums, mapping
from app.lib.web import responses
from app.lib.web.errors import RuleValidationError
from app.presentation.server.handlers import common


class ColumnDescriptionSchema(Schema):
    name = fields.Str(required=True, description="Name of the column")
    data_type = fields.Str(required=True, description="Type of data", validate=validate.OneOf(mapping.type_map.keys()))
    unit = fields.Str(required=True, description="Unit of the data", example="m/s")
    description = fields.Str(load_default="", description="Human-readable description of the column")

    @post_load
    def make(self, data, **kwargs) -> model.ColumnDescription:
        return model.ColumnDescription(**data)


class CreateTableRequestSchema(Schema):
    table_name = fields.Str(required=True, description="Name of the table")
    columns = fields.List(
        fields.Nested(ColumnDescriptionSchema), required=True, description="List of columns in the table"
    )
    bibcode = fields.Str(
        required=True,
        description="ADS bibcode of the article that published the data (or code of the internal communication)",
        example="2024NatAs.tmp..120M",
    )
    datatype = fields.Str(
        load_default="regular",
        description="Type of the data in the table",
        validate=validate.OneOf([e.value for e in enums.DataType]),
    )
    description = fields.Str(load_default="", description="Human-readable description of the table")

    @post_load
    def make(self, data, **kwargs) -> model.CreateTableRequest:
        return model.CreateTableRequest(**data)


# def wrap_response_schema(source_schema: type) -> type:
#     class WrappedResponseSchema(Schema):
#         data = fields.Nested(source_schema, required=True)

#     WrappedResponseSchema.__name__ = source_schema.__name__
#     WrappedResponseSchema.somenonsence = "here"
#     return WrappedResponseSchema


class CreateTableResponseSchema(Schema):
    id = fields.Int(description="Output id of the table", required=True)

# CreateTableResponseSchema = wrap_response_schema(CreateTableResponseSchema)


async def create_table_handler(depot: commands.Depot, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Create table with unprocessed data
    description: Describes schema of the table without any data.
    tags: [admin, table]
    security:
        - TokenAuth: []
    requestBody:
        content:
            application/json:
                schema: CreateTableRequestSchema
    responses:
        200:
            description: Table was successfully created
            content:
                application/json:
                    schema: CreateTableResponseSchema
    """
    request_dict = await r.json()
    try:
        request = CreateTableRequestSchema().load(request_dict)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.create_table(depot, request))


description = common.HandlerDescription(
    common.HTTPMethod.POST,
    "/api/v1/admin/table",
    create_table_handler,
    CreateTableRequestSchema,
    CreateTableResponseSchema,
)
