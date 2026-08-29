from typing import final

from app.data import model
from app.dataapi import clients, repository, responders
from app.dataapi.domain import parameterized_query, reddening
from app.dataapi.presentation import interface
from app.lib.tap import types as tap_types
from app.lib.web import errors
from app.specs import dataapi as spec

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
class Actions(interface.Actions):
    def __init__(
        self,
        repo: repository.Repository,
        catalog_cfg: responders.CatalogConfig,
        fieldapi_client: clients.FieldAPIClient,
    ) -> None:
        self.repo = repo
        self.catalog_cfg = catalog_cfg
        self.reddening = reddening.Reddening(repo, fieldapi_client)
        self.parameterized_query_manager = parameterized_query.ParameterizedQueryManager(
            repo, ENABLED_CATALOGS, catalog_cfg, self.reddening
        )

    def query_simple(self, query: spec.QuerySimpleRequest) -> spec.QuerySimpleResponse:
        return self.parameterized_query_manager.query_simple(query)

    def tap_tables(self, request: spec.ListTAPTablesRequest) -> spec.ListTAPTablesResponse:
        include_columns = request.detail == spec.Detail.MAX
        tables = self.repo.list_tables_with_columns(
            sorted(METADATA_ALLOWED_SCHEMAS),
            include_columns=include_columns,
        )
        schemas: dict[str, list[spec.TAPTableInfo]] = {}
        for table in tables:
            columns: list[spec.TAPColumnInfo] | None = None
            if include_columns:
                columns = [
                    spec.TAPColumnInfo(
                        name=c.column_name,
                        datatype=tap_types.pg_to_tap_datatype(c.data_type),
                        unit=c.unit,
                        ucd=c.ucd,
                        description=c.description,
                    )
                    for c in table.columns
                ]
            schemas.setdefault(table.schema_name, []).append(
                spec.TAPTableInfo(
                    name=f'{table.schema_name}."{table.table_name}"',
                    type="table",
                    description=table.description,
                    columns=columns,
                )
            )
        return spec.ListTAPTablesResponse(
            schemas=[
                spec.TAPSchemaEntry(schema_name=schema_name, tables=schema_tables)
                for schema_name, schema_tables in sorted(schemas.items())
            ]
        )

    def tap_sync(self, request: spec.TAPSyncRequest) -> spec.TAPSyncResponse:
        result = self.repo.query_with_metadata(request.query, request.maxrec)
        columns: list[spec.TAPVOTableColumn] = []
        for col in result.columns:
            datatype = tap_types.python_to_tap_datatype(col.sample_value)
            columns.append(
                spec.TAPVOTableColumn(
                    name=col.column_name,
                    datatype=datatype,
                    arraysize="*" if datatype == "char" else None,
                )
            )
        data = [[_json_cell(cell) for cell in row] for row in result.rows]
        return spec.TAPSyncResponse(
            resource=spec.TAPVOTableResource(
                table=spec.TAPVOTableTable(columns=columns, data=data),
            )
        )

    def calculate_reddening(self, request: spec.CalculateReddeningRequest) -> spec.CalculateReddeningResponse:
        queries = [
            reddening.ReddeningQuery(photsys=request.photsys, coordinate=coordinate)
            for coordinate in request.coordinates
        ]
        results = self.reddening.calculate(queries)
        if not results[0].filters:
            raise errors.NotFoundError("Photometric system", request.photsys)
        return spec.CalculateReddeningResponse(photsys=request.photsys, results=results)

    def list_reddening_references(self) -> spec.ListReddeningReferencesResponse:
        return self.reddening.list_references()
