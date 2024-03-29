from marshmallow import Schema, fields, post_load, validate

from app.domain import model


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


class SearchCatalogsResponseSchema(Schema):
    catalogs = fields.List(
        fields.Nested(CatalogSchema),
        description="List of catalogs with tables and various metadata",
    )


class ChooseTableRequestSchema(Schema):
    catalog_id = fields.Str(required=True, description="ID of the catalog to select")
    table_id = fields.Str(required=True, description="ID of the table to select")

    @post_load
    def make(self, data, **kwargs) -> model.ChooseTableRequest:
        return model.ChooseTableRequest(**data)


class ChooseTableResponseSchema(Schema):
    id = fields.Int(description="Processing pipeline ID")
