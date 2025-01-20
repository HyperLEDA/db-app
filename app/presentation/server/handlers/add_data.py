from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import commands, schema
from app.domain import actions
from app.lib.web import responses, server
from app.lib.web.errors import RuleValidationError
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
        example=[
            {"name": "M 33", "ra": 1.5641, "dec": 30.6602},
            {"name": "M 31", "ra": 0.7123, "dec": 41.2690},
        ],
    )

    @post_load
    def make(self, data, **kwargs) -> schema.AddDataRequest:
        return schema.AddDataRequest(**data)


class AddDataResponseSchema(Schema):
    pass


async def add_data_handler(depot: commands.Depot, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Add new raw data to the table
    description: |
        Inserts new data to the table.

        Deduplicates the rows based on their contents.
        If the two rows were identical this method will only insert the last one.
    security:
        - TokenAuth: []
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
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.add_data(depot, request))


description = common.handler_description(
    server.HTTPMethod.POST,
    "/api/v1/admin/table/data",
    add_data_handler,
    AddDataRequestSchema,
    AddDataResponseSchema,
)
