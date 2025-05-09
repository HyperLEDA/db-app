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
            "example": {"ra": {"column_name": "ra"}, "dec": {"column_name": "dec"}},
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
            "example": {"e_ra": 0.1, "e_dec": 0.2},
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
    description: |
        Creates new marking rules to map the columns in the table to catalog parameters. For a given table a marking
        would consist of the mapping between catalog parameters and the columns from the original table.

        For example, if one wants to create a marking for a column `object_name` that designates the name of an object,
        they should create a catalog entry similar to the following:
        ```json
        {
            "name": "designation",
            "parameters": {
                "design": {
                    "column_name": "object_name"
                }
            }
        }
        ```

        Here, `name` respresents the name of the catalog, keys of `parameters` map are parameter names and `column_name`
        values are actual names of the columns under question. **For now, only one column per parameter is supported.**

        It is possible to create several catalog entries for a single object, for example - is there are two columns
        that represent a name of an object. In that case we might want to upload both names to the database so it is
        easier to cross-identify and search these objects later. Another use case might be if there are several columns
        that represent photometric information in different filters. In that case one might want to create one entry
        for each of the magnitude columns.

        In that case you can specify several entries into `rules` list with different values of `key`. For example:

        ```json
        {
            "table_name": "my_table",
            "rules": [
                {
                    "name": "designation",
                    "parameters": {
                        "design": {
                            "column_name": "object_name"
                        }
                    },
                    "key": "primary_name"
                },
                {
                    "name": "designation",
                    "parameters": {
                        "design": {
                            "column_name": "secondary_object_name"
                        }
                    },
                    "key": "secondary_name"
                }
            ]
        }
        ```

        The result of this would be two entries into the `designation` catalog for each object in the original table.

        This handler also supports additional parameters that are not present in the original table. For example, a
        table might not have a separate column for astrometric errors but from other sources you know that its error is
        0.1 degrees for right ascension and 0.5 degrees for declination. You can specify this in the
        `additional_parameters` field for each catalog:

        ```json
        {
            "name": "icrs",
            "parameters": {
                "ra": {
                    "column_name": "RAJ2000"
                },
                "dec": {
                    "column_name": "DEJ2000"
                }
            },
            "additional_parameters": {
                "e_ra": 0.1,
                "e_dec": 0.5
            }
        }
        ```
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
