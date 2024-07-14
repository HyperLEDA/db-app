from typing import Any

from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import commands
from app.domain import actions, model
from app.lib.exceptions import RuleValidationError
from app.lib.storage import enums, mapping
from app.presentation.server.handlers import common


class ColumnDescriptionSchema(Schema):
    name = fields.Str(required=True, description="Name of the column")
    data_type = fields.Str(required=True, description="Type of data", validate=validate.OneOf(mapping.type_map.keys()))
    unit = fields.Str(required=True, description="Unit of the data")
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


class CreateTableResponseSchema(Schema):
    id = fields.Int(description="Output id of the table", required=True)


async def create_table_handler(depot: commands.Depot, r: web.Request) -> Any:
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
                    schema:
                        type: object
                        properties:
                            data: CreateTableResponseSchema
    """
    request_dict = await r.json()
    try:
        request = CreateTableRequestSchema().load(request_dict)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return actions.create_table(depot, request)


description = common.HandlerDescription(
    common.HTTPMethod.POST,
    "/api/v1/admin/table",
    create_table_handler,
    CreateTableRequestSchema,
    CreateTableResponseSchema,
)
