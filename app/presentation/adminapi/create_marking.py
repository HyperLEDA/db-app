from aiohttp import web
from marshmallow import Schema, ValidationError, fields, validate
from marshmallow_generic import GenericSchema

from app.data import model
from app.lib.web import responses
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


class ParameterSchema(GenericSchema[interface.ParameterToMark]):
    column_name = fields.String(
        required=True,
        metadata={
            "description": "Column that this parameter will be mapped to.",
            "example": "ra",
        },
    )
    enrichment = fields.Dict(
        required=False,
        metadata={
            "description": "Additional information about the column, such as units.",
            "example": {},
        },
    )


class CatalogSchema(GenericSchema[interface.CatalogToMark]):
    name = fields.Str(required=True, validate=validate.OneOf([cat.value for cat in model.RawCatalog]))
    parameters = fields.Dict(
        required=True,
        metadata={
            "description": "Map of parameter names to their configurations",
            "example": {},
        },
        keys=fields.String(),
        values=fields.Nested(ParameterSchema),
        validate=validate.Length(1),
    )
    key = fields.String(required=False)
    additional_params = fields.Dict(
        required=False,
        metadata={
            "description": "Additional parameters for the catalog",
            "example": {},
        },
    )


class CreateMarkingRequestSchema(GenericSchema[interface.CreateMarkingRequest]):
    table_name = fields.String(required=True, metadata={"description": "Table to which apply the marking rules to."})
    catalogs = fields.List(fields.Nested(CatalogSchema), required=True, validate=validate.Length(1))


class CreateMarkingResponseSchema(Schema):
    pass


async def create_marking_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: New marking rules for the table
    description: Creates new marking rules to map the columns in the table to catalog parameters.
    security:
        - TokenAuth: []
    tags: [table]
    requestBody:
        content:
            application/json:
                schema: CreateMarkingRequestSchema
    responses:
        200:
            description: Homogenization rules were successfully created
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: CreateMarkingResponseSchema
    """
    request_dict = await r.json()
    try:
        request = CreateMarkingRequestSchema().load(request_dict)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.create_marking(request))
