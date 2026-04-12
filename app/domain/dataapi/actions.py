from typing import final

from app.data import model, repositories
from app.domain import responders
from app.domain.dataapi import parameterized_query, search_parsers
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
METADATA_BLACKLISTED_TABLES: frozenset[tuple[str, str]] = frozenset(
    {
        ("common", "users"),
        ("common", "tokens"),
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
        entries = self.metadata_repo.list_schemas()
        visible: list[dataapi.SchemaEntry] = []
        for e in entries:
            if e.schema_name not in METADATA_ALLOWED_SCHEMAS:
                continue
            tables = [
                dataapi.TableSummary(table_name=t.table_name, description=t.description)
                for t in e.tables
                if (e.schema_name, t.table_name) not in METADATA_BLACKLISTED_TABLES
            ]
            visible.append(
                dataapi.SchemaEntry(schema_name=e.schema_name, description=e.description, tables=tables),
            )
        return dataapi.ListSchemasResponse(schemas=visible)

    def get_table(self, request: dataapi.GetTableRequest) -> dataapi.GetTableResponse:
        if request.schema_name not in METADATA_ALLOWED_SCHEMAS:
            raise errors.NotFoundError("Table", f"{request.schema_name}.{request.table_name}")
        if (request.schema_name, request.table_name) in METADATA_BLACKLISTED_TABLES:
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
