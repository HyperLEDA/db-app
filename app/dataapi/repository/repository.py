import math
from collections.abc import Mapping, Sequence
from typing import Any, final

import structlog
from astropy import units as u

from app import catalogs
from app.catalogs import designation_normalization
from app.dataapi import model
from app.dataapi.repository import model as repo_model
from app.lib import astronomy, concurrency
from app.lib.storage import postgres

_ONE_TO_ONE_CATALOGS = frozenset(
    {
        catalogs.RawCatalog.DESIGNATION,
        catalogs.RawCatalog.ICRS,
        catalogs.RawCatalog.REDSHIFT,
        catalogs.RawCatalog.NATURE,
    }
)

_ONE_TO_MANY_CATALOGS = frozenset(
    {
        catalogs.RawCatalog.ADDITIONAL_DESIGNATIONS,
        catalogs.RawCatalog.NOTE,
        catalogs.RawCatalog.PHOTOMETRY__TOTAL,
    }
)


def _description_from_param(param: Any) -> str | None:
    if param is None:
        return None
    if not isinstance(param, dict):
        return None
    d = param.get("description")
    if d is None:
        return None
    return str(d) if d != "" else None


def _infer_column_sample(column: str, rows: list[dict[str, Any]]) -> object | None:
    for row in rows:
        value = row[column]
        if value is not None:
            return value
    return None


_TAP_SYNC_QUERY_TIMEOUT_SECONDS = 20
_SPHERE_RADIUS_M = 6371008.7714


@final
class Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def find_pgcs_by_designation(self, name: str, limit: int, offset: int) -> list[int]:
        stripped = name.strip() if name else ""
        if not stripped:
            return []
        normalized = designation_normalization.normalize_designation(name)
        names = [stripped] if normalized == stripped else [stripped, normalized]
        rows = self._storage.query(
            """
            SELECT pgc
            FROM (
                SELECT DISTINCT ON (d.pgc)
                    d.pgc,
                    CASE
                        WHEN d.design ILIKE t.term THEN 0
                        WHEN d.design ILIKE t.term || '%%' THEN 1
                        ELSE 2
                    END AS match_class,
                    strpos(lower(d.design), lower(t.term)) AS match_pos,
                    length(d.design) AS design_len
                FROM layer2.designations AS d
                CROSS JOIN unnest(%s::text[]) AS t(term)
                WHERE d.design ILIKE '%%' || t.term || '%%'
                ORDER BY d.pgc, match_class, match_pos, design_len
            ) best
            ORDER BY match_class, match_pos, design_len, pgc
            LIMIT %s OFFSET %s
            """,
            params=[names, limit, offset],
        )
        return [int(row["pgc"]) for row in rows]

    def find_pgcs_by_equatorial(
        self,
        ra: float,
        dec: float,
        radius: u.Quantity,
        limit: int,
        offset: int,
    ) -> list[int]:
        radius_m = math.radians(astronomy.to(radius, "deg")) * _SPHERE_RADIUS_M
        rows = self._storage.query(
            """
            SELECT pgc
            FROM layer2.icrs
            WHERE ST_DWithin(
                ST_MakePoint(%s, %s)::geography,
                ST_MakePoint(ra, dec)::geography,
                %s,
                false
            )
            ORDER BY ST_Distance(
                ST_MakePoint(%s, %s)::geography,
                ST_MakePoint(ra, dec)::geography,
                false
            ), pgc
            LIMIT %s OFFSET %s
            """,
            params=[ra, dec, radius_m, ra, dec, limit, offset],
        )
        return [int(row["pgc"]) for row in rows]

    def find_pgcs_unfiltered(self, limit: int, offset: int) -> list[int]:
        rows = self._storage.query(
            """
            SELECT id
            FROM common.pgc
            ORDER BY id
            LIMIT %s OFFSET %s
            """,
            params=[limit, offset],
        )
        return [int(row["id"]) for row in rows]

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

    def get_table_metadata(self, schema: str, table: str) -> postgres.TableInfo:
        return postgres.get_table_metadata(self._storage, schema, table)

    def list_tables_with_columns(
        self,
        schemas: Sequence[str],
        *,
        include_columns: bool,
    ) -> list[postgres.TableInfo]:
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
        result: list[postgres.TableInfo] = []
        for row in table_rows:
            schema_name = row["schema_name"]
            table_name = row["table_name"]
            if include_columns:
                result.append(self.get_table_metadata(schema_name, table_name))
            else:
                result.append(
                    postgres.TableInfo(
                        schema=schema_name,
                        name=table_name,
                        description=_description_from_param(row.get("param")),
                        columns={},
                        primary_keys=set(),
                    )
                )
        return result

    def query_catalogs(
        self,
        raw_catalogs: list[catalogs.RawCatalog],
        pgcs: list[int],
    ) -> list[model.Layer2Object]:
        if not raw_catalogs or not pgcs:
            return []

        one_to_one = [c for c in raw_catalogs if c in _ONE_TO_ONE_CATALOGS]
        one_to_many = [c for c in raw_catalogs if c in _ONE_TO_MANY_CATALOGS]

        errgr = concurrency.ErrorGroup()
        one_to_one_task: concurrency.TaskResult[_OneToOneMaps] | None = None
        additional_designations_task: concurrency.TaskResult[dict[int, model.AdditionalDesignationsCatalog]] | None = (
            None
        )
        notes_task: concurrency.TaskResult[dict[int, model.NotesCatalog]] | None = None
        photometry_total_task: concurrency.TaskResult[dict[int, model.PhotometryTotalCatalog]] | None = None

        if one_to_one:
            one_to_one_task = errgr.run(self._query_one_to_one_catalogs, one_to_one, pgcs)
        if catalogs.RawCatalog.ADDITIONAL_DESIGNATIONS in one_to_many:
            additional_designations_task = errgr.run(self._query_additional_designations, pgcs)
        if catalogs.RawCatalog.NOTE in one_to_many:
            notes_task = errgr.run(self._query_notes, pgcs)
        if catalogs.RawCatalog.PHOTOMETRY__TOTAL in one_to_many:
            photometry_total_task = errgr.run(self._query_photometry_total, pgcs)

        errgr.wait()

        one_to_one_maps = one_to_one_task.result() if one_to_one_task is not None else _OneToOneMaps.empty()
        additional_designations_map = (
            additional_designations_task.result() if additional_designations_task is not None else {}
        )
        notes_map = notes_task.result() if notes_task is not None else {}
        photometry_total_map = photometry_total_task.result() if photometry_total_task is not None else {}

        return [
            _layer2_object_from_maps(
                pgc,
                raw_catalogs,
                one_to_one_maps.designation,
                additional_designations_map,
                one_to_one_maps.icrs,
                one_to_one_maps.redshift,
                one_to_one_maps.nature,
                notes_map,
                photometry_total_map,
            )
            for pgc in pgcs
        ]

    def _query_one_to_one_catalogs(
        self,
        raw_catalogs: list[catalogs.RawCatalog],
        pgcs: list[int],
    ) -> "_OneToOneMaps":
        columns: list[str] = ["t.pgc"]
        join_parts: list[str] = []

        for catalog in raw_catalogs:
            object_cls = catalogs.get_catalog_object_type(catalog)
            table_name = object_cls.layer2_table()
            join_parts.append(f"LEFT JOIN {table_name} USING (pgc)")
            for column in object_cls.layer2_keys():
                columns.append(f'{table_name}.{column} AS "{catalog.value}|{column}"')
            columns.append(
                f'CASE WHEN {table_name}.pgc IS NOT NULL THEN true ELSE false END AS "{catalog.value}|_present"'
            )

        query = f"""
            SELECT {", ".join(columns)}
            FROM unnest(%s::int[]) WITH ORDINALITY AS t(pgc, ord)
            {" ".join(join_parts)}
            ORDER BY t.ord
        """
        rows = self._storage.query(query, params=[pgcs])
        return _parse_one_to_one_rows(rows, raw_catalogs)

    def _query_additional_designations(self, pgcs: list[int]) -> dict[int, model.AdditionalDesignationsCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, design, code, year, author, title FROM layer2.designations "
            "WHERE pgc = ANY(%s) ORDER BY pgc, design",
            params=[pgcs],
        )
        result: dict[int, list[model.AdditionalDesignation]] = {}
        for row in rows:
            pgc = int(row["pgc"])
            ad = model.AdditionalDesignation(
                name=str(row["design"]) if row.get("design") is not None else "",
                source=_source_from_row(row),
            )
            result.setdefault(pgc, []).append(ad)
        return {pgc: model.AdditionalDesignationsCatalog(names=names) for pgc, names in result.items()}

    def _query_notes(self, pgcs: list[int]) -> dict[int, model.NotesCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, note, code, year, author, title FROM layer2.notes WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        result: dict[int, list[model.NoteEntry]] = {}
        for row in rows:
            pgc = int(row["pgc"])
            note = model.NoteEntry(
                note=str(row["note"]) if row.get("note") is not None else "",
                source=_source_from_row(row),
            )
            result.setdefault(pgc, []).append(note)
        return {pgc: model.NotesCatalog(notes=notes) for pgc, notes in result.items()}

    def _query_photometry_total(self, pgcs: list[int]) -> dict[int, model.PhotometryTotalCatalog]:
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
        result: dict[int, list[model.PhotometryTotalMeasurement]] = {}
        for row in rows:
            pgc = int(row["pgc"])
            measurement = model.PhotometryTotalMeasurement(
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
        return {pgc: model.PhotometryTotalCatalog(measurements=measurements) for pgc, measurements in result.items()}


@final
class _OneToOneMaps:
    def __init__(
        self,
        designation: dict[int, model.DesignationCatalog],
        icrs: dict[int, model.ICRSCatalog],
        redshift: dict[int, model.RedshiftCatalog],
        nature: dict[int, model.NatureCatalog],
    ) -> None:
        self.designation = designation
        self.icrs = icrs
        self.redshift = redshift
        self.nature = nature

    @classmethod
    def empty(cls) -> "_OneToOneMaps":
        return cls({}, {}, {}, {})


def _parse_one_to_one_rows(
    rows: list[Mapping[str, Any]],
    raw_catalogs: list[catalogs.RawCatalog],
) -> _OneToOneMaps:
    designation: dict[int, model.DesignationCatalog] = {}
    icrs: dict[int, model.ICRSCatalog] = {}
    redshift: dict[int, model.RedshiftCatalog] = {}
    nature: dict[int, model.NatureCatalog] = {}

    for row in rows:
        pgc = int(row["pgc"])
        data_by_catalog: dict[catalogs.RawCatalog, dict[str, Any]] = {}
        presence: dict[catalogs.RawCatalog, bool] = {}

        for key, value in row.items():
            if key == "pgc":
                continue
            catalog_name, column = key.split("|", 1)
            catalog = catalogs.RawCatalog(catalog_name)
            if column == "_present":
                presence[catalog] = bool(value)
            else:
                data_by_catalog.setdefault(catalog, {})[column] = value

        for catalog in raw_catalogs:
            if not presence.get(catalog, False):
                continue
            data = data_by_catalog.get(catalog, {})
            if catalog == catalogs.RawCatalog.DESIGNATION:
                designation[pgc] = model.DesignationCatalog(name=str(data["design"]))
            elif catalog == catalogs.RawCatalog.ICRS:
                if all(data.get(k) is not None for k in ("ra", "e_ra", "dec", "e_dec")):
                    icrs[pgc] = model.ICRSCatalog(
                        ra=float(data["ra"]),
                        e_ra=float(data["e_ra"]),
                        dec=float(data["dec"]),
                        e_dec=float(data["e_dec"]),
                    )
            elif catalog == catalogs.RawCatalog.REDSHIFT:
                if data.get("cz") is not None and data.get("e_cz") is not None:
                    redshift[pgc] = model.RedshiftCatalog(cz=float(data["cz"]), e_cz=float(data["e_cz"]))
            elif catalog == catalogs.RawCatalog.NATURE:
                if data.get("type_name") is not None:
                    nature[pgc] = model.NatureCatalog(type_name=str(data["type_name"]))

    return _OneToOneMaps(designation, icrs, redshift, nature)


def _layer2_object_from_maps(
    pgc: int,
    raw_catalogs: list[catalogs.RawCatalog],
    designation_map: dict[int, model.DesignationCatalog],
    additional_designations_map: dict[int, model.AdditionalDesignationsCatalog],
    icrs_map: dict[int, model.ICRSCatalog],
    redshift_map: dict[int, model.RedshiftCatalog],
    nature_map: dict[int, model.NatureCatalog],
    notes_map: dict[int, model.NotesCatalog],
    photometry_total_map: dict[int, model.PhotometryTotalCatalog],
) -> model.Layer2Object:
    designation = designation_map.get(pgc) if catalogs.RawCatalog.DESIGNATION in raw_catalogs else None
    additional_designations = (
        additional_designations_map.get(pgc) if catalogs.RawCatalog.ADDITIONAL_DESIGNATIONS in raw_catalogs else None
    )
    icrs = icrs_map.get(pgc) if catalogs.RawCatalog.ICRS in raw_catalogs else None
    redshift = redshift_map.get(pgc) if catalogs.RawCatalog.REDSHIFT in raw_catalogs else None
    nature = nature_map.get(pgc) if catalogs.RawCatalog.NATURE in raw_catalogs else None
    notes = notes_map.get(pgc) if catalogs.RawCatalog.NOTE in raw_catalogs else None
    photometry_total = photometry_total_map.get(pgc) if catalogs.RawCatalog.PHOTOMETRY__TOTAL in raw_catalogs else None

    return model.Layer2Object(
        pgc=pgc,
        catalogs=model.Catalogs(
            designation=designation,
            additional_designations=additional_designations,
            icrs=icrs,
            redshift=redshift,
            nature=nature,
            notes=notes,
            photometry_total=photometry_total,
        ),
    )


def _source_from_row(row: Mapping[str, Any]) -> model.Source:
    author_val = row.get("author")
    authors = author_val if isinstance(author_val, list) else [str(author_val)] if author_val is not None else []
    return model.Source(
        bibcode=str(row["code"]) if row.get("code") is not None else "",
        title=str(row["title"]) if row.get("title") is not None else "",
        authors=authors,
        year=int(row["year"]) if row.get("year") is not None else 0,
    )
