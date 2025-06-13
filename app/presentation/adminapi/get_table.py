from aiohttp import web
from marshmallow import Schema, ValidationError, fields
from marshmallow_generic import GenericSchema

from app.lib.web import responses
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface
from app.presentation.adminapi.create_table import ColumnDescriptionSchema


class BibliographySchema(Schema):
    title = fields.Str(metadata={"description": "Title of publication"})
    authors = fields.List(fields.Str(), metadata={"description": "List of authors"})
    year = fields.Int(metadata={"description": "Year of the publication"})
    bibcode = fields.Str(metadata={"description": "Bibcode reference"})


class GetTableRequestSchema(GenericSchema[interface.GetTableRequest]):
    table_name = fields.Str(required=True, metadata={"description": "Name of the table"})


class GetTableResponseSchema(Schema):
    id = fields.Int(metadata={"description": "ID of the table"})
    description = fields.Str(metadata={"description": "Table description"})
    column_info = fields.List(
        fields.Nested(ColumnDescriptionSchema), metadata={"description": "List of columns in the table"}
    )
    rows_num = fields.Int(metadata={"description": "Number of rows"})
    meta = fields.Dict(keys=fields.Str(), metadata={"description": "Table metadata"})
    bibliography = fields.Nested(BibliographySchema, metadata={"description": "Table bibliography"})


async def get_table_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    try:
        request = GetTableRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.get_table(request))
