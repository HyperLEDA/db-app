from typing import Any

from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import common


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


async def add_data_handler(actions: domain.Actions, r: web.Request) -> Any:
    """---
    summary: Add new raw data to the table
    description: Inserts new data to the table.
    tags: [admin, table]
    requestBody:
        content:
            application/json:
                schema: AddDataRequestSchema
    responses:
        200:
            description: Source was successfully created
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: AddDataResponseSchema
    """
    request_dict = await r.json()
    try:
        request = AddDataRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.add_data(request)


description = common.HandlerDescription(
    common.HTTPMethod.POST,
    "/api/v1/admin/table/data",
    add_data_handler,
    AddDataRequestSchema,
    AddDataResponseSchema,
)