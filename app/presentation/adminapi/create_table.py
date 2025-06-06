from aiohttp import web
from marshmallow import Schema, ValidationError, fields, validate
from marshmallow_generic import GenericSchema

from app.lib.storage import enums, mapping
from app.lib.web import responses
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


class ColumnDescriptionSchema(GenericSchema[interface.ColumnDescription]):
    name = fields.Str(
        required=True,
        metadata={"description": "Name of the column. Should not equal `hyperleda_internal_id`."},
    )
    data_type = fields.Str(
        required=True,
        validate=validate.OneOf(mapping.type_map.keys()),
        metadata={"description": "Type of data"},
    )
    unit = fields.Str(
        allow_none=True,
        metadata={"description": "Unit of the data", "example": "m/s"},
    )
    ucd = fields.Str(
        allow_none=True,
        metadata={
            "description": "Unified Content Descriptor for the column (UCD1+)",
            "example": "pos.eq.ra",
        },
    )
    description = fields.Str(
        allow_none=True,
        load_default="",
        metadata={"description": "Human-readable description of the column"},
    )


class CreateTableRequestSchema(GenericSchema[interface.CreateTableRequest]):
    table_name = fields.Str(required=True, metadata={"description": "Name of the table"})
    columns = fields.List(
        fields.Nested(ColumnDescriptionSchema),
        required=True,
        metadata={
            "description": "List of columns in the table",
            "example": [  # minimal set of working columns
                {"name": "name", "data_type": "str", "ucd": "meta.id"},
                {"name": "ra", "data_type": "float", "unit": "hourangle", "ucd": "pos.eq.ra"},
                {"name": "dec", "data_type": "float", "unit": "deg", "ucd": "pos.eq.dec"},
            ],
        },
    )
    bibcode = fields.Str(
        required=True,
        metadata={
            "description": "ADS bibcode of the article that published the data (or code of the internal communication)",
            "example": "2024PDU....4601628D",
        },
    )
    datatype = fields.Str(
        allow_none=True,
        load_default="regular",
        validate=validate.OneOf([e.value for e in enums.DataType]),
        metadata={"description": "Type of the data in the table"},
    )
    description = fields.Str(
        allow_none=True,
        load_default="",
        metadata={"description": "Human-readable description of the table"},
    )


class CreateTableResponseSchema(Schema):
    id = fields.Int(required=True, metadata={"description": "Output id of the table"})


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
