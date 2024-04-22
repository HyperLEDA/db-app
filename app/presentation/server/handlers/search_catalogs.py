import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import Schema, ValidationError, fields, post_load, validate

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error


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
    query = fields.Str(required=True, description="Query for catalog searching")
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


@docs(
    summary="Obtain list of catalogs",
    tags=["table"],
    description="Obtains a list of catalogs according to query.",
)
@querystring_schema(
    SearchCatalogsRequestSchema(),
    example=dataclasses.asdict(model.SearchCatalogsRequest("dss", 10)),
)
@response_schema(SearchCatalogsResponseSchema(), 200)
async def search_catalogs_handler(actions: domain.Actions, r: web.Request) -> Any:
    try:
        request = SearchCatalogsRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.search_catalogs(request)
