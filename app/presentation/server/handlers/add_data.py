from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import Schema, ValidationError, fields, post_load

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error


class AddDataRequestSchema(Schema):
    table_id = fields.Int(required=True, description="ID of the table to add data to")
    data = fields.List(
        fields.Dict(fields.Str),
        required=True,
        description="""
            Actual data to append. 
            Keys in this dictionary must be a subset of the columns in the table. 
            If not specified, column will be set to NULL.
        """,
    )

    @post_load
    def make(self, data, **kwargs) -> model.AddDataRequest:
        return model.AddDataRequest(**data)


class AddDataResponseSchema(Schema):
    pass


@docs(
    summary="Add new raw data to the table",
    tags=["table", "admin"],
    description="Inserts new data to the table.",
)
@request_schema(AddDataRequestSchema())
@response_schema(AddDataResponseSchema(), 200)
async def add_data_handler(actions: domain.Actions, r: web.Request) -> Any:
    request_dict = await r.json()
    try:
        request = AddDataRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.add_data(request)
