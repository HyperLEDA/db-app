from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import commands, schema
from app.domain import actions
from app.lib.storage import enums, mapping
from app.lib.web import responses
from app.lib.web.errors import RuleValidationError
from app.presentation.server.handlers import common


class ColumnDescriptionSchema(Schema):
    name = fields.Str(required=True, description="Name of the column. Should not equal `hyperleda_internal_id`.")
    data_type = fields.Str(required=True, description="Type of data", validate=validate.OneOf(mapping.type_map.keys()))
    unit = fields.Str(allow_none=True, description="Unit of the data", example="m/s")
    ucd = fields.Str(
        allow_none=True, description="Unified Content Descriptor for the column (UCD1+)", example="pos.eq.ra"
    )
    description = fields.Str(allow_none=True, load_default="", description="Human-readable description of the column")

    @post_load
    def make(self, data, **kwargs) -> schema.ColumnDescription:
        return schema.ColumnDescription(**data)


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
        allow_none=True,
        load_default="regular",
        description="Type of the data in the table",
        validate=validate.OneOf([e.value for e in enums.DataType]),
    )
    description = fields.Str(allow_none=True, load_default="", description="Human-readable description of the table")

    @post_load
    def make(self, data, **kwargs) -> schema.CreateTableRequest:
        return schema.CreateTableRequest(**data)


class CreateTableResponseSchema(Schema):
    id = fields.Int(description="Output id of the table", required=True)


async def create_table_handler(depot: commands.Depot, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Get or create schema for the table.
    description: |
        Creates new schema for the table which can later be used to upload data.

        **Important**: If the table with the specified name already exists, does nothing and returns ID
        of the previously created table without any alterations.
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
        201:
            description: Table with this name already existed, its ID is returned
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

    result, created = actions.create_table(depot, request)

    if created:
        return responses.APIOkResponse(result)

    return responses.APIOkResponse(result, status=201)


description = common.HandlerDescription(
    common.HTTPMethod.POST,
    "/api/v1/admin/table",
    create_table_handler,
    CreateTableRequestSchema,
    CreateTableResponseSchema,
)
