from aiohttp import web
from marshmallow import Schema, ValidationError, fields
from marshmallow_generic import GenericSchema

from app.lib.web import responses
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


class AddDataRequestSchema(GenericSchema[interface.AddDataRequest]):
    table_id = fields.Integer(
        required=True,
        metadata={
            "description": "ID of the table to add data to",
        },
    )
    data = fields.List(
        fields.Dict(fields.Str),
        required=True,
        metadata={
            "description": """Actual data to append. 
                Keys in this dictionary must be a subset of the columns in the table. 
                If not specified, column will be set to NULL.

                NaN and NULL are considered to be the same thing.""",
            "example": [
                {"name": "M 33", "ra": 1.5641, "dec": 30.6602},
                {"name": "M 31", "ra": 0.7123, "dec": 41.2690},
            ],
        },
    )


class AddDataResponseSchema(Schema):
    pass


async def add_data_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Add new raw data to the table
    description: |
        Inserts new data to the table.

        Deduplicates rows based on their contents.
        If two rows were identical this method will only insert the last one.
    security:
        - TokenAuth: []
    tags: [table]
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

    return responses.APIOkResponse(actions.add_data(request))
