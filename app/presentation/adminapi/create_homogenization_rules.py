from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load, validate

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


class HomogenizationRuleSchema(Schema):
    catalog = fields.Str(required=True, validate=validate.OneOf([cat.value for cat in model.RawCatalog]))
    parameter = fields.Str(
        required=True,
        description="Parameter name for the catalog. See the documentation for the catalog.",
        example="ra",
    )
    key = fields.Str(required=False)
    filters = fields.Dict(
        required=True,
        description="Filters that determine which column will be used as a parameter for the catalog.",
        example={"ucd": "pos.eq.ra"},
        validate=filter_validator,
    )
    enrichment = fields.Dict(
        required=False,
        description="Additional information about the column, such as units.",
        example={},
    )

    @post_load
    def post_load(self, data, **kwargs) -> model.HomogenizationRule:
        return model.HomogenizationRule(**data)


class CreateHomogenizationRulesRequestSchema(schema.RequestSchema):
    rules = fields.List(fields.Nested(HomogenizationRuleSchema), required=True)

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
