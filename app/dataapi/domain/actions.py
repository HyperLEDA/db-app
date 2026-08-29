from typing import final

from app.data import model, repositories
from app.dataapi import clients, responders
from app.dataapi.domain import parameterized_query
from app.dataapi.presentation import interface
from app.lib.tap import types as tap_types
from app.lib.web import errors
from app.specs import dataapi as spec
from app.specs import fieldapi as fieldapi_spec

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
        layer2_repo: repositories.Layer2Repository,
        catalog_cfg: responders.CatalogConfig,
        metadata_repo: repositories.MetadataRepository,
        references_repo: repositories.ReferencesRepository,
        fieldapi_client: clients.FieldAPIClient,
    ) -> None:
        self.layer2_repo = layer2_repo
        self.catalog_cfg = catalog_cfg
        self.metadata_repo = metadata_repo
        self.references_repo = references_repo
        self.fieldapi_client = fieldapi_client
        self.parameterized_query_manager = parameterized_query.ParameterizedQueryManager(
            layer2_repo, ENABLED_CATALOGS, catalog_cfg
        )

    def query_simple(self, query: spec.QuerySimpleRequest) -> spec.QuerySimpleResponse:
        return self.parameterized_query_manager.query_simple(query)

    def tap_tables(self, request: spec.ListTAPTablesRequest) -> spec.ListTAPTablesResponse:
        include_columns = request.detail == spec.Detail.MAX
        tables = self.metadata_repo.list_tables_with_columns(
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
        result = self.metadata_repo.query_with_metadata(request.query, request.maxrec)
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
        coefficients = self.references_repo.list_reddening(request.photsys)
        if not coefficients:
            raise errors.NotFoundError("Photometric system", request.photsys)

        sky_coordinates = [
            fieldapi_spec.SkyCoordinate(ra_deg=coordinate.ra, dec_deg=coordinate.dec)
            for coordinate in request.coordinates
        ]
        ebv_values = self.fieldapi_client.sample_sfd_ebv(sky_coordinates)

        results = [
            spec.ReddeningAtPosition(
                ebv=ebv,
                filters=[
                    spec.ReddeningFilterValue(
                        filter=coefficient.filter,
                        wavelength=coefficient.lambda_eff,
                        a=coefficient.a_ebv * ebv,
                    )
                    for coefficient in coefficients
                ],
            )
            for ebv in ebv_values
        ]
        return spec.CalculateReddeningResponse(photsys=request.photsys, results=results)

    def list_reddening_references(self) -> spec.ListReddeningReferencesResponse:
        systems = self.references_repo.list_reddening_systems()
        return spec.ListReddeningReferencesResponse(
            systems=[
                spec.ReddeningPhotometricSystem(id=system.id, description=system.description) for system in systems
            ]
        )
