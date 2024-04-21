from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error
from app.lib.storage import enums, mapping


class ColumnDescriptionSchema(Schema):
    name = fields.Str(required=True, description="Name of the column")
    data_type = fields.Str(required=True, description="Type of data", validate=validate.OneOf(mapping.type_map.keys()))
    unit = fields.Str(required=True, description="Unit of the data")
    description = fields.Str(load_deafult="", description="Human-readable description of the column")

    @post_load
    def make(self, data, **kwargs) -> model.ColumnDescription:
        return model.ColumnDescription(**data)


class CreateTableRequestSchema(Schema):
    table_name = fields.Str(required=True, description="Name of the table")
    columns = fields.List(
        fields.Nested(ColumnDescriptionSchema), required=True, description="List of columns in the table"
    )
    bibliography_id = fields.Int(required=True, description="ID of the bibliographic data assosiated with this table")
    datatype = fields.Str(
        load_default="regular",
        description="Type of the data in the table",
        validate=validate.OneOf([e.value for e in enums.DataType]),
    )
    description = fields.Str(load_deafult="", description="Human-readable description of the table")

    @post_load
    def make(self, data, **kwargs) -> model.CreateTableRequest:
        return model.CreateTableRequest(**data)


class CreateTableResponseSchema(Schema):
    id = fields.Int(description="Output id of the table")


@docs(
    summary="Create table with unprocessed data",
    tags=["table", "admin"],
    description="Describes schema of the table without any data.",
)
@request_schema(CreateTableRequestSchema())
@response_schema(CreateTableResponseSchema(), 200)
async def create_table_handler(actions: domain.Actions, r: web.Request) -> Any:
    request_dict = await r.json()
    try:
        request = CreateTableRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.create_table(request)
