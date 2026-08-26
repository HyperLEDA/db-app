from typing import final

from app.data import model, repositories
from app.dataapi import presentation as dataapi
from app.dataapi import responders
from app.dataapi.domain import parameterized_query
from app.lib.tap import types as tap_types

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
        "distance",
        "morphology",
    },
)


def _json_cell(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


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

    def query_simple(self, query: dataapi.QuerySimpleRequest) -> dataapi.QuerySimpleResponse:
        return self.parameterized_query_manager.query_simple(query)

    def tap_tables(self, request: dataapi.ListTAPTablesRequest) -> dataapi.ListTAPTablesResponse:
        include_columns = request.detail == dataapi.Detail.MAX
        tables = self.metadata_repo.list_tables_with_columns(
            sorted(METADATA_ALLOWED_SCHEMAS),
            include_columns=include_columns,
        )
        schemas: dict[str, list[dataapi.TAPTableInfo]] = {}
        for table in tables:
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
                    name=f'{table.schema_name}."{table.table_name}"',
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

    def tap_sync(self, request: dataapi.TAPSyncRequest) -> dataapi.TAPSyncResponse:
        result = self.metadata_repo.query_with_metadata(request.query, request.maxrec)
        columns: list[dataapi.TAPVOTableColumn] = []
        for col in result.columns:
            datatype = tap_types.python_to_tap_datatype(col.sample_value)
            columns.append(
                dataapi.TAPVOTableColumn(
                    name=col.column_name,
                    datatype=datatype,
                    arraysize="*" if datatype == "char" else None,
                )
            )
        data = [[_json_cell(cell) for cell in row] for row in result.rows]
        return dataapi.TAPSyncResponse(
            resource=dataapi.TAPVOTableResource(
                table=dataapi.TAPVOTableTable(columns=columns, data=data),
            )
        )
