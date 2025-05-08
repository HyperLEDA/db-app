from aiohttp import web
from marshmallow import Schema, ValidationError, fields, validate

from app.data import model
from app.domain import homogenization
from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


def filter_validator(filters: dict[str, str]):
    try:
        homogenization.parse_filters(filters)
    except ValueError as e:
        raise ValidationError(str(e)) from e


class ParameterSchema(schema.RequestSchema):
    filters = fields.Dict(
        required=True,
        metadata={
            "description": "Filters that determine which column will be used as a parameter for the catalog.",
            "example": {"ucd": "pos.eq.ra"},
        },
        validate=filter_validator,
    )
    enrichment = fields.Dict(
        required=False,
        metadata={
            "description": "Additional information about the column, such as units.",
            "example": {},
        },
    )

    class Meta:
        model = interface.HomogenizationParameter


class CatalogSchema(schema.RequestSchema):
    name = fields.Str(required=True, validate=validate.OneOf([cat.value for cat in model.RawCatalog]))
    parameters = fields.Dict(
        required=True,
        metadata={
            "description": "Map of parameter names to their configurations",
            "example": {},
        },
        keys=fields.Str(),
        values=fields.Nested(ParameterSchema),
    )
    key = fields.Str(required=False)
    additional_params = fields.Dict(
        required=False,
        metadata={
            "description": "Additional parameters for the catalog",
            "example": {},
        },
    )

    class Meta:
        model = interface.HomogenizationCatalog


class CreateHomogenizationRulesRequestSchema(schema.RequestSchema):
    catalogs = fields.List(fields.Nested(CatalogSchema), required=True)

    class Meta:
        model = interface.CreateHomogenizationRulesRequest


class CreateHomogenizationRulesResponseSchema(Schema):
    pass


async def create_homogenization_rules_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: New homogenization rules
    description: Creates new homogenization rules in the database.
    security:
        - TokenAuth: []
    tags: [homogenization]
    requestBody:
        content:
            application/json:
                schema: CreateHomogenizationRulesRequestSchema
    responses:
        200:
            description: Homogenization rules were successfully created
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: CreateHomogenizationRulesResponseSchema
    """
    request_dict = await r.json()
    try:
        request = CreateHomogenizationRulesRequestSchema().load(request_dict)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.create_homogenization_rules(request))
