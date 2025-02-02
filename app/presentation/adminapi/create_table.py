from aiohttp import web
from marshmallow import Schema, ValidationError, fields, validate

from app.lib.storage import enums, mapping
from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


class ColumnDescriptionSchema(schema.RequestSchema):
    name = fields.Str(required=True, description="Name of the column. Should not equal `hyperleda_internal_id`.")
    data_type = fields.Str(required=True, description="Type of data", validate=validate.OneOf(mapping.type_map.keys()))
    unit = fields.Str(allow_none=True, description="Unit of the data", example="m/s")
    ucd = fields.Str(
        allow_none=True, description="Unified Content Descriptor for the column (UCD1+)", example="pos.eq.ra"
    )
    description = fields.Str(allow_none=True, load_default="", description="Human-readable description of the column")

    class Meta:
        model = interface.ColumnDescription


class CreateTableRequestSchema(schema.RequestSchema):
    table_name = fields.Str(required=True, description="Name of the table")
    columns = fields.List(
        fields.Nested(ColumnDescriptionSchema),
        required=True,
        description="List of columns in the table",
        example=[  # minimal set of working columns
            {"name": "name", "data_type": "str", "ucd": "meta.id"},
            {"name": "ra", "data_type": "float", "unit": "hourangle", "ucd": "pos.eq.ra"},
            {"name": "dec", "data_type": "float", "unit": "deg", "ucd": "pos.eq.dec"},
        ],
    )
    bibcode = fields.Str(
        required=True,
        description="ADS bibcode of the article that published the data (or code of the internal communication)",
        example="2024PDU....4601628D",
    )
    datatype = fields.Str(
        allow_none=True,
        load_default="regular",
        description="Type of the data in the table",
        validate=validate.OneOf([e.value for e in enums.DataType]),
    )
    description = fields.Str(allow_none=True, load_default="", description="Human-readable description of the table")

    class Meta:
        model = interface.CreateTableRequest


class CreateTableResponseSchema(Schema):
    id = fields.Int(description="Output id of the table", required=True)


async def create_table_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Get or create schema for the table.
    description: |
        Creates new schema for the table which can later be used to upload data.

        **Important**: If the table with the specified name already exists, does nothing and returns ID
        of the previously created table without any alterations.
    tags: [table]
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

    result, created = actions.create_table(request)

    if created:
        return responses.APIOkResponse(result)

    return responses.APIOkResponse(result, status=201)
