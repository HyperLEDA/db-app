import json
from collections.abc import Mapping, Sequence
from typing import Any, final

import structlog
from psycopg import rows

from app.data import model
from app.data.model import Layer2Object
from app.data.model import layer2 as layer2_model
from app.dataapi.repository import filters as repofilters
from app.dataapi.repository import model as repo_model
from app.dataapi.repository import params
from app.lib import concurrency, containers
from app.lib.storage import postgres


def _description_from_param(param: Any) -> str | None:
    if param is None:
        return None
    if not isinstance(param, dict):
        return None
    d = param.get("description")
    if d is None:
        return None
    return str(d) if d != "" else None


def _column_detail_from_row(row: dict[str, Any]) -> repo_model.MetadataColumnDetail:
    param = row.get("param") or {}
    if not isinstance(param, dict):
        param = {}
    return repo_model.MetadataColumnDetail(
        column_name=row["column_name"],
        data_type=row.get("data_type"),
        description=param.get("description"),
        unit=param.get("unit"),
        ucd=param.get("ucd"),
    )


def _infer_column_sample(column: str, rows: list[dict[str, Any]]) -> object | None:
    for row in rows:
        value = row[column]
        if value is not None:
            return value
    return None


_TAP_SYNC_QUERY_TIMEOUT_SECONDS = 20


@final
class Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def list_reddening_systems(self, r_v: str = "3.1") -> list[repo_model.ReddeningPhotometricSystem]:
        rows = self._storage.query(
            """
            SELECT DISTINCT s.id, s.description
            FROM photometry.reddening r
            JOIN photometry.systems s ON s.id = r.photsys
            WHERE r.r_v = %s::photometry.r_v_type
            ORDER BY s.id
            """,
            params=[r_v],
        )
        return [
            repo_model.ReddeningPhotometricSystem(
                id=row["id"],
                description=row["description"],
            )
            for row in rows
        ]

    def list_reddening(self, photsys: str, r_v: str = "3.1") -> list[repo_model.ReddeningCoefficient]:
        rows = self._storage.query(
            """
            SELECT filter, lambda_eff, a_ebv
            FROM photometry.reddening
            WHERE photsys = %s AND r_v = %s::photometry.r_v_type
            ORDER BY lambda_eff
            """,
            params=[photsys, r_v],
        )
        return [
            repo_model.ReddeningCoefficient(
                filter=row["filter"],
                lambda_eff=float(row["lambda_eff"]),
                a_ebv=float(row["a_ebv"]),
            )
            for row in rows
        ]

    def query_with_metadata(
        self,
        query: str,
        max_rows: int,
        *,
        timeout_seconds: float = _TAP_SYNC_QUERY_TIMEOUT_SECONDS,
    ) -> repo_model.QueryWithMetadataResult:
        stripped = query.strip().rstrip(";")
        wrapped = f"SELECT * FROM ({stripped}\n) AS _tap_sync\nLIMIT {max_rows}"
        dict_rows: list[dict[str, Any]] = self._storage.query(
            wrapped,
            timeout_seconds=timeout_seconds,
            read_only=True,
        )
        if not dict_rows:
            return repo_model.QueryWithMetadataResult(columns=[], rows=[])
        col_names = list(dict_rows[0].keys())
        columns = [
            repo_model.QueryColumnMetadata(column_name=name, sample_value=_infer_column_sample(name, dict_rows))
            for name in col_names
        ]
        result_rows = [[row[name] for name in col_names] for row in dict_rows]
        return repo_model.QueryWithMetadataResult(columns=columns, rows=result_rows)

    def list_tables_with_columns(
        self,
        schemas: Sequence[str],
        *,
        include_columns: bool,
    ) -> list[repo_model.MetadataTableDetail]:
        if not schemas:
            return []

        table_rows = self._storage.query(
            """
            SELECT schema_name, table_name, param
            FROM meta.table_info
            WHERE schema_name = ANY(%s)
            ORDER BY schema_name, table_name
            """,
            params=[list(schemas)],
        )
        columns_by_table: dict[tuple[str, str], list[repo_model.MetadataColumnDetail]] = {}
        if include_columns:
            column_rows = self._storage.query(
                """
                SELECT c.table_schema AS schema_name,
                       c.table_name,
                       c.column_name,
                       c.data_type::text AS data_type,
                       ci.param
                FROM information_schema.columns c
                INNER JOIN meta.column_info ci
                  ON ci.schema_name = c.table_schema
                 AND ci.table_name = c.table_name
                 AND ci.column_name = c.column_name
                WHERE c.table_schema = ANY(%s)
                ORDER BY c.table_schema, c.table_name, c.ordinal_position
                """,
                params=[list(schemas)],
            )
            for row in column_rows:
                key = (row["schema_name"], row["table_name"])
                columns_by_table.setdefault(key, []).append(_column_detail_from_row(row))

        return [
            repo_model.MetadataTableDetail(
                schema_name=row["schema_name"],
                table_name=row["table_name"],
                description=_description_from_param(row.get("param")),
                columns=columns_by_table.get((row["schema_name"], row["table_name"]), []),
            )
            for row in table_rows
        ]

    def query_catalogs_batch(
        self,
        catalogs: list[model.RawCatalog],
        search_types: Mapping[str, repofilters.Filter],
        search_params: Mapping[str, params.SearchParams],
        limit: int,
        offset: int,
        ordering: repofilters.Ordering | None = None,
    ) -> dict[str, list[model.Layer2CatalogObject]]:
        query, query_params = _construct_batch_query(
            catalogs, search_types, search_params, limit, offset, ordering=ordering
        )

        records = self._storage.query(query, params=query_params)

        records_by_id = containers.group_by(records, key_func=lambda obj: str(obj["record_id"]))

        result: dict[str, list[model.Layer2CatalogObject]] = {}

        for record_id, record_rows in records_by_id.items():
            if record_id not in result:
                result[record_id] = []

            result[record_id].extend(_group_by_pgc(record_rows))

        return result

    def query_pgc(
        self,
        catalogs: list[model.RawCatalog],
        pgc_numbers: list[int],
        limit: int,
        offset: int = 0,
    ) -> list[Layer2Object]:
        if not catalogs or not pgc_numbers:
            return []

        pgcs_page = sorted(pgc_numbers)[offset : offset + limit]
        if not pgcs_page:
            return []

        errgr = concurrency.ErrorGroup()
        designation_task: concurrency.TaskResult[dict[int, layer2_model.DesignationCatalog]] | None = None
        additional_designations_task: (
            concurrency.TaskResult[dict[int, layer2_model.AdditionalDesignationsCatalog]] | None
        ) = None
        icrs_task: concurrency.TaskResult[dict[int, layer2_model.ICRSCatalog]] | None = None
        redshift_task: concurrency.TaskResult[dict[int, layer2_model.RedshiftCatalog]] | None = None
        nature_task: concurrency.TaskResult[dict[int, layer2_model.NatureCatalog]] | None = None
        notes_task: concurrency.TaskResult[dict[int, layer2_model.NotesCatalog]] | None = None
        photometry_total_task: concurrency.TaskResult[dict[int, layer2_model.PhotometryTotalCatalog]] | None = None

        if model.RawCatalog.DESIGNATION in catalogs:
            designation_task = errgr.run(self._query_designations, pgcs_page)
        if model.RawCatalog.ADDITIONAL_DESIGNATIONS in catalogs:
            additional_designations_task = errgr.run(self._query_additional_designations, pgcs_page)
        if model.RawCatalog.ICRS in catalogs:
            icrs_task = errgr.run(self._query_icrs, pgcs_page)
        if model.RawCatalog.REDSHIFT in catalogs:
            redshift_task = errgr.run(self._query_redshift, pgcs_page)
        if model.RawCatalog.NATURE in catalogs:
            nature_task = errgr.run(self._query_nature, pgcs_page)
        if model.RawCatalog.NOTE in catalogs:
            notes_task = errgr.run(self._query_notes, pgcs_page)
        if model.RawCatalog.PHOTOMETRY__TOTAL in catalogs:
            photometry_total_task = errgr.run(self._query_photometry_total, pgcs_page)

        errgr.wait()

        designation_map = designation_task.result() if designation_task is not None else {}
        additional_designations_map = (
            additional_designations_task.result() if additional_designations_task is not None else {}
        )
        icrs_map = icrs_task.result() if icrs_task is not None else {}
        redshift_map = redshift_task.result() if redshift_task is not None else {}
        nature_map = nature_task.result() if nature_task is not None else {}
        notes_map = notes_task.result() if notes_task is not None else {}
        photometry_total_map = photometry_total_task.result() if photometry_total_task is not None else {}

        return [
            _layer2_object_from_maps(
                pgc,
                catalogs,
                designation_map,
                additional_designations_map,
                icrs_map,
                redshift_map,
                nature_map,
                notes_map,
                photometry_total_map,
            )
            for pgc in pgcs_page
        ]

    def query_catalogs(
        self,
        catalogs: list[model.RawCatalog],
        filters: repofilters.Filter,
        search_params: params.SearchParams,
        limit: int,
        offset: int,
        ordering: repofilters.Ordering | None = None,
    ) -> list[model.Layer2CatalogObject]:
        res = self.query_catalogs_batch(
            catalogs,
            {search_params.name(): filters},
            {"obj": search_params},
            limit,
            offset,
            ordering=ordering,
        )

        if "obj" not in res:
            return []

        return res["obj"]

    def _query_designations(self, pgcs: list[int]) -> dict[int, layer2_model.DesignationCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, design FROM layer2.designation WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        return {int(row["pgc"]): layer2_model.DesignationCatalog(name=str(row["design"])) for row in rows}

    def _query_icrs(self, pgcs: list[int]) -> dict[int, layer2_model.ICRSCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, ra, e_ra, dec, e_dec FROM layer2.icrs WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        result: dict[int, layer2_model.ICRSCatalog] = {}
        for row in rows:
            if all(row.get(k) is not None for k in ("ra", "e_ra", "dec", "e_dec")):
                result[int(row["pgc"])] = layer2_model.ICRSCatalog(
                    ra=float(row["ra"]),
                    e_ra=float(row["e_ra"]),
                    dec=float(row["dec"]),
                    e_dec=float(row["e_dec"]),
                )
        return result

    def _query_redshift(self, pgcs: list[int]) -> dict[int, layer2_model.RedshiftCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, cz, e_cz FROM layer2.cz WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        return {
            int(row["pgc"]): layer2_model.RedshiftCatalog(cz=float(row["cz"]), e_cz=float(row["e_cz"]))
            for row in rows
            if row.get("cz") is not None and row.get("e_cz") is not None
        }

    def _query_nature(self, pgcs: list[int]) -> dict[int, layer2_model.NatureCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, type_name FROM layer2.nature WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        return {
            int(row["pgc"]): layer2_model.NatureCatalog(type_name=str(row["type_name"]))
            for row in rows
            if row.get("type_name") is not None
        }

    def _query_additional_designations(self, pgcs: list[int]) -> dict[int, layer2_model.AdditionalDesignationsCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, design, code, year, author, title FROM layer2.designations "
            "WHERE pgc = ANY(%s) ORDER BY pgc, design",
            params=[pgcs],
        )
        result: dict[int, list[layer2_model.AdditionalDesignation]] = {}
        for row in rows:
            pgc = int(row["pgc"])
            ad = layer2_model.AdditionalDesignation(
                name=str(row["design"]) if row.get("design") is not None else "",
                source=_source_from_row(row),
            )
            result.setdefault(pgc, []).append(ad)
        return {pgc: layer2_model.AdditionalDesignationsCatalog(names=names) for pgc, names in result.items()}

    def _query_notes(self, pgcs: list[int]) -> dict[int, layer2_model.NotesCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, note, code, year, author, title FROM layer2.notes WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        result: dict[int, list[layer2_model.NoteEntry]] = {}
        for row in rows:
            pgc = int(row["pgc"])
            note = layer2_model.NoteEntry(
                note=str(row["note"]) if row.get("note") is not None else "",
                source=_source_from_row(row),
            )
            result.setdefault(pgc, []).append(note)
        return {pgc: layer2_model.NotesCatalog(notes=notes) for pgc, notes in result.items()}

    def _query_photometry_total(self, pgcs: list[int]) -> dict[int, layer2_model.PhotometryTotalCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            """
            SELECT p.pgc, p.band, p.magsys, p.method, p.wavelength, p.mag, p.e_mag,
                   b.photsys, b.name AS filter
            FROM layer2.photometry_total AS p
              JOIN photometry.calib_bands AS cb ON p.band = cb.id
              JOIN photometry.bands AS b ON cb.band = b.id
            WHERE p.pgc = ANY(%s)
            ORDER BY p.pgc, p.wavelength
            """,
            params=[pgcs],
        )
        result: dict[int, list[layer2_model.PhotometryTotalMeasurement]] = {}
        for row in rows:
            pgc = int(row["pgc"])
            measurement = layer2_model.PhotometryTotalMeasurement(
                band=str(row["band"]),
                magsys=str(row["magsys"]) if row.get("magsys") is not None else None,
                method=str(row["method"]),
                wavelength=float(row["wavelength"]),
                mag=float(row["mag"]),
                e_mag=float(row["e_mag"]) if row.get("e_mag") is not None else None,
                photsys=str(row["photsys"]),
                filter=str(row["filter"]),
            )
            result.setdefault(pgc, []).append(measurement)
        return {
            pgc: layer2_model.PhotometryTotalCatalog(measurements=measurements) for pgc, measurements in result.items()
        }


def _driving_table(search_types: Mapping[str, repofilters.Filter]) -> str | None:
    tables: set[str] = set()
    for search_filter in search_types.values():
        try:
            tables.add(search_filter.driving_table())
        except NotImplementedError:
            return None
    if len(tables) != 1:
        return None
    return tables.pop()


def _construct_batch_query(
    catalogs: list[model.RawCatalog],
    search_types: Mapping[str, repofilters.Filter],
    search_params: Mapping[str, params.SearchParams],
    limit: int,
    offset: int,
    ordering: repofilters.Ordering | None = None,
) -> tuple[str, list[Any]]:
    if not search_params:
        return "SELECT NULL as record_id, NULL as pgc WHERE FALSE", []

    query = """
            WITH search_params AS (
                SELECT * FROM (
                    VALUES 
                        {values}
                ) AS t(record_id, search_type, params)
            ) 
            SELECT sp.record_id, pgc, {columns}
            FROM search_params sp
            CROSS JOIN {joined_tables}
            WHERE {conditions}
            {order_by}
            LIMIT %s OFFSET %s
        """

    values_lines = []
    query_params = []

    for record_id, sparams in search_params.items():
        values_lines.append("(%s, %s, %s::jsonb)")
        query_params.extend([record_id, sparams.name(), json.dumps(sparams.get_params())])

    columns = []
    table_names = []

    for catalog in catalogs:
        object_cls = model.get_catalog_object_type(catalog)

        table_names.append(object_cls.layer2_table())
        columns.extend(
            [
                f'{object_cls.layer2_table()}.{column} AS "{catalog.value}|{column}"'
                for column in object_cls.layer2_keys()
            ]
        )
        columns.append(
            f"CASE WHEN {object_cls.layer2_table()}.pgc IS NOT NULL "
            f'THEN true ELSE false END AS "{catalog.value}|_present"'
        )

    driving_table = _driving_table(search_types)

    if driving_table is not None:
        other_tables = [table_name for table_name in table_names if table_name != driving_table]
        joined_tables = " LEFT JOIN ".join(
            [driving_table] + [f"{table_name} USING (pgc)" for table_name in other_tables]
        )
    else:
        joined_tables = " FULL JOIN ".join(
            [f"{table_names[0]}"] + [f"{table_name} USING (pgc)" for table_name in table_names[1:]]
        )

    condition_statements = []

    for search_type, search_filter in search_types.items():
        condition_statements.append(f"(sp.search_type = '{search_type}' AND {search_filter.get_query()})")
        query_params.extend(search_filter.get_params())

    if ordering is not None:
        query_params.extend(ordering.get_params())

    query_params.extend([limit, offset])

    return query.format(
        values=",".join(values_lines),
        columns=",".join(columns),
        joined_tables=joined_tables,
        conditions=" OR ".join(condition_statements),
        order_by=f"ORDER BY {ordering.get_query()}" if ordering is not None else "",
    ), query_params


def _group_by_pgc(objects: list[rows.DictRow]) -> list[model.Layer2CatalogObject]:
    objects_by_pgc = containers.group_by(objects, key_func=lambda obj: int(obj["pgc"]))
    result = []

    for pgc, pgc_objects in objects_by_pgc.items():
        layer2_obj = model.Layer2CatalogObject(pgc, [])

        obj = pgc_objects[0]
        if "record_id" in obj:
            obj.pop("record_id")
        if "pgc" in obj:
            obj.pop("pgc")

        res: dict[model.RawCatalog, dict[str, Any]] = {}
        presence_flags: dict[model.RawCatalog, bool] = {}

        for key, value in obj.items():
            catalog_name, column = key.split("|")
            catalog = model.RawCatalog(catalog_name)

            if column == "_present":
                presence_flags[catalog] = bool(value)
            else:
                if catalog not in res:
                    res[catalog] = {}
                res[catalog][column] = value

        for catalog, data in res.items():
            object_cls = model.get_catalog_object_type(catalog)

            if presence_flags.get(catalog, False):
                layer2_obj.data.append(object_cls.from_layer2(data))

        result.append(layer2_obj)

    return result


def _layer2_object_from_maps(
    pgc: int,
    catalogs: list[model.RawCatalog],
    designation_map: dict[int, layer2_model.DesignationCatalog],
    additional_designations_map: dict[int, layer2_model.AdditionalDesignationsCatalog],
    icrs_map: dict[int, layer2_model.ICRSCatalog],
    redshift_map: dict[int, layer2_model.RedshiftCatalog],
    nature_map: dict[int, layer2_model.NatureCatalog],
    notes_map: dict[int, layer2_model.NotesCatalog],
    photometry_total_map: dict[int, layer2_model.PhotometryTotalCatalog],
) -> Layer2Object:
    designation = designation_map.get(pgc) if model.RawCatalog.DESIGNATION in catalogs else None
    additional_designations = (
        additional_designations_map.get(pgc) if model.RawCatalog.ADDITIONAL_DESIGNATIONS in catalogs else None
    )
    icrs = icrs_map.get(pgc) if model.RawCatalog.ICRS in catalogs else None
    redshift = redshift_map.get(pgc) if model.RawCatalog.REDSHIFT in catalogs else None
    nature = nature_map.get(pgc) if model.RawCatalog.NATURE in catalogs else None
    notes = notes_map.get(pgc) if model.RawCatalog.NOTE in catalogs else None
    photometry_total = photometry_total_map.get(pgc) if model.RawCatalog.PHOTOMETRY__TOTAL in catalogs else None

    return Layer2Object(
        pgc=pgc,
        catalogs=layer2_model.Catalogs(
            designation=designation,
            additional_designations=additional_designations,
            icrs=icrs,
            redshift=redshift,
            nature=nature,
            notes=notes,
            photometry_total=photometry_total,
        ),
    )


def _source_from_row(row: Mapping[str, Any]) -> layer2_model.Source:
    author_val = row.get("author")
    authors = author_val if isinstance(author_val, list) else [str(author_val)] if author_val is not None else []
    return layer2_model.Source(
        bibcode=str(row["code"]) if row.get("code") is not None else "",
        title=str(row["title"]) if row.get("title") is not None else "",
        authors=authors,
        year=int(row["year"]) if row.get("year") is not None else 0,
    )
