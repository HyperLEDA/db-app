from typing import Any

from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import common


class FieldSchema(Schema):
    id = fields.Str(description="Field name")
    description = fields.Str(description="Field description")
    unit = fields.Str(description="Unit of measurements")


class TableSchema(Schema):
    id = fields.Str(description="Table id")
    num_rows = fields.Int(description="Number of rows in the table")
    fields_data = fields.List(
        fields.Nested(FieldSchema),
        description="List of fields in the table with their metadata",
        data_key="fields",
    )


class CatalogSchema(Schema):
    id = fields.Str(description="Vizier ID of the catalog")
    description = fields.Str(description="Description of the catalog")
    url = fields.Str(description="Link to the catalog")
    bibcode = fields.Str(description="Catalog bibliography")
    tables = fields.List(
        fields.Nested(TableSchema),
        description="List of tables with their metadata",
    )


class SearchCatalogsRequestSchema(Schema):
    query = fields.Str(required=True, description="Query for catalog searching", example="dss")
    page_size = fields.Int(
        load_default=10,
        description="Maximum number of catalogs to return",
        validate=validate.OneOf([5, 10, 20]),
    )

    @post_load
    def make(self, data, **kwargs) -> model.SearchCatalogsRequest:
        return model.SearchCatalogsRequest(**data)


class SearchCatalogsResponseSchema(Schema):
    catalogs = fields.List(
        fields.Nested(CatalogSchema),
        description="List of catalogs with tables and various metadata",
    )


async def search_catalogs_handler(actions: domain.Actions, r: web.Request) -> Any:
    """---
    summary: Obtain list of catalogs
    description: Obtains a list of catalogs according to query.
    tags: [table]
    parameters:
      - in: query
        schema: SearchCatalogsRequestSchema
    responses:
        200:
            description: Query successfully returned results.
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: SearchCatalogsResponseSchema
    """
    try:
        request = SearchCatalogsRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.search_catalogs(request)


description = common.HandlerDescription(
    common.HTTPMethod.GET,
    "/api/v1/pipeline/catalogs",
    search_catalogs_handler,
    SearchCatalogsRequestSchema,
    SearchCatalogsResponseSchema,
)
