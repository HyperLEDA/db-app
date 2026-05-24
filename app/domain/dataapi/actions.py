from typing import final

from app.data import model, repositories
from app.domain import responders
from app.domain.dataapi import parameterized_query, search_parsers, tap_types
from app.lib.web import errors
from app.presentation import dataapi

ENABLED_CATALOGS = [
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.ICRS,
    model.RawCatalog.REDSHIFT,
    model.RawCatalog.NATURE,
]

METADATA_ALLOWED_SCHEMAS = frozenset(
    {
        "common",
        "rawdata",
        "designation",
        "icrs",
        "cz",
        "layer2",
        "layer0",
        "nature",
        "note",
        "photometry",
    },
)


@final
class Actions(dataapi.Actions):
    def __init__(
        self,
        layer2_repo: repositories.Layer2Repository,
        catalog_cfg: responders.CatalogConfig,
        metadata_repo: repositories.MetadataRepository,
    ) -> None:
        self.layer2_repo = layer2_repo
        self.catalog_cfg = catalog_cfg
        self.metadata_repo = metadata_repo
        self.parameterized_query_manager = parameterized_query.ParameterizedQueryManager(
            layer2_repo, ENABLED_CATALOGS, catalog_cfg
        )

    def query(self, query: dataapi.QueryRequest) -> dataapi.QueryResponse:
        filters, search_params = search_parsers.query_to_filters(query.q, search_parsers.DEFAULT_PARSERS)
        objects = self.layer2_repo.query_catalogs(
            ENABLED_CATALOGS,
            filters,
            search_params,
            query.page_size,
            query.page,
        )
        responder = responders.StructuredResponder(self.catalog_cfg)
        pgc_objects = responder.build_response_from_catalog(objects).objects
        return dataapi.QueryResponse(objects=pgc_objects)

    def query_fits(self, query: dataapi.FITSRequest) -> bytes:
        return self.parameterized_query_manager.query_fits(query)

    def query_simple(self, query: dataapi.QuerySimpleRequest) -> dataapi.QuerySimpleResponse:
        return self.parameterized_query_manager.query_simple(query)

    def list_schemas(self) -> dataapi.ListSchemasResponse:
        entries = self.metadata_repo.list_schemas(METADATA_ALLOWED_SCHEMAS)
        return dataapi.ListSchemasResponse(
            schemas=[
                dataapi.SchemaEntry(
                    schema_name=e.schema_name,
                    description=e.description,
                    tables=[dataapi.TableSummary(table_name=t.table_name, description=t.description) for t in e.tables],
                )
                for e in entries
            ],
        )

    def get_table(self, request: dataapi.GetTableRequest) -> dataapi.GetTableResponse:
        if request.schema_name not in METADATA_ALLOWED_SCHEMAS:
            raise errors.NotFoundError("Table", f"{request.schema_name}.{request.table_name}")
        detail = self.metadata_repo.get_table(request.schema_name, request.table_name)
        if detail is None:
            raise errors.NotFoundError("Table", f"{request.schema_name}.{request.table_name}")
        raw_rows = self.metadata_repo.fetch_table_sample_rows(request.schema_name, request.table_name)
        sample_rows = [{k: str(v) for k, v in row.items()} for row in raw_rows]
        return dataapi.GetTableResponse(
            schema_name=detail.schema_name,
            table_name=detail.table_name,
            description=detail.description,
            columns=[
                dataapi.ColumnInfo(
                    column_name=c.column_name,
                    data_type=c.data_type,
                    description=c.description,
                    unit=c.unit,
                    ucd=c.ucd,
                )
                for c in detail.columns
            ],
            sample_rows=sample_rows,
        )

    def list_tap_tables(self, request: dataapi.ListTAPTablesRequest) -> dataapi.ListTAPTablesResponse:
        include_columns = request.detail == dataapi.Detail.MAX
        tables = self.metadata_repo.list_tables_with_columns(
            sorted(METADATA_ALLOWED_SCHEMAS),
            include_columns=include_columns,
        )
        schemas: dict[str, list[dataapi.TAPTableInfo]] = {}
        for table in tables:
            if (table.schema_name, table.table_name) in METADATA_BLACKLISTED_TABLES:
                continue
            columns: list[dataapi.TAPColumnInfo] | None = None
            if include_columns:
                columns = [
                    dataapi.TAPColumnInfo(
                        name=c.column_name,
                        datatype=tap_types.pg_to_tap_datatype(c.data_type),
                        unit=c.unit,
                        ucd=c.ucd,
                        description=c.description,
                    )
                    for c in table.columns
                ]
            schemas.setdefault(table.schema_name, []).append(
                dataapi.TAPTableInfo(
                    name=f"{table.schema_name}.{table.table_name}",
                    type="table",
                    description=table.description,
                    columns=columns,
                )
            )
        return dataapi.ListTAPTablesResponse(
            schemas=[
                dataapi.TAPSchemaEntry(schema_name=schema_name, tables=schema_tables)
                for schema_name, schema_tables in sorted(schemas.items())
            ]
        )
