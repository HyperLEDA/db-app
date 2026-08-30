import hashlib
import json
import uuid
from collections.abc import Callable, Iterable

import astropy.io.votable.ucd as ucd
import pandas
import regex
import structlog
from astropy import units
from astropy import units as u
from astroquery import nasa_ads as ads

from app.adminapi import cache, clients, model, repository
from app.adminapi.domain import table_stats
from app.lib import astronomy, concurrency
from app.lib.storage import enums, mapping, postgres
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.specs import adminapi as spec

BIBCODE_REGEX = "^([0-9]{4}[A-Za-z.&]{5}[A-Za-z0-9.]{4}[AELPQ-Z0-9.][0-9.]{4}[A-Z])$"

FORBIDDEN_COLUMN_NAMES = {repository.INTERNAL_ID_COLUMN_NAME}

logger = structlog.stdlib.get_logger()


def _column_meta(schema: postgres.TableInfo, name: str) -> tuple[str, str]:
    col = schema.columns.get(name)
    if col is None:
        return ("", "")
    return (col.description or "", col.unit or "")


def _build_catalog_schema(
    designation_schema: postgres.TableInfo,
    icrs_schema: postgres.TableInfo,
    nature_schema: postgres.TableInfo,
    nature_object_types: dict[str, str],
) -> spec.RecordCatalogSchema:
    design_desc, _ = _column_meta(designation_schema, "design")
    ra_desc, ra_unit = _column_meta(icrs_schema, "ra")
    e_ra_desc, e_ra_unit = _column_meta(icrs_schema, "e_ra")
    dec_desc, dec_unit = _column_meta(icrs_schema, "dec")
    e_dec_desc, e_dec_unit = _column_meta(icrs_schema, "e_dec")
    type_name_desc, _ = _column_meta(nature_schema, "type_name")
    return spec.RecordCatalogSchema(
        designation=spec.RecordDesignationCatalogSchema(
            description=spec.RecordDesignationCatalogDescriptionSchema(name=design_desc),
        ),
        icrs=spec.RecordICRSCatalogSchema(
            unit=spec.RecordICRSCatalogUnitSchema(
                ra=ra_unit,
                ra_error=e_ra_unit,
                dec=dec_unit,
                dec_error=e_dec_unit,
            ),
            description=spec.RecordICRSCatalogDescriptionSchema(
                ra=ra_desc,
                ra_error=e_ra_desc,
                dec=dec_desc,
                dec_error=e_dec_desc,
            ),
        ),
        redshift=spec.RecordRedshiftCatalogSchema(
            description=spec.RecordRedshiftCatalogDescriptionSchema(
                z="Heliocentric redshift",
                z_error="Heliocentric redshift error",
            ),
        ),
        nature=spec.RecordNatureCatalogSchema(
            description=spec.RecordNatureCatalogDescriptionSchema(
                type_name=type_name_desc,
                types=nature_object_types,
            ),
        ),
    )


class TableUploadManager:
    def __init__(
        self,
        repo: repository.Repository,
        clients: clients.Clients,
        table_stats_cache: cache.BackgroundCache[spec.TableStatsSnapshot],
    ) -> None:
        self._repo = repo
        self.clients = clients
        self.table_stats_cache = table_stats_cache

    def create_table(self, r: spec.CreateTableRequest) -> tuple[spec.CreateTableResponse, bool]:
        source_id = ensure_source_id(self._repo, self.clients.ads, r.bibcode)

        for col in r.columns:
            if col.name in FORBIDDEN_COLUMN_NAMES:
                raise RuleValidationError(f"{col} is a reserved column name")

        table_info = domain_descriptions_to_data(r.table_name, r.columns, r.description)

        table_resp = self._repo.create_table(
            model.Layer0TableMeta(
                table_info=table_info,
                bibliography_id=source_id,
                datatype=enums.DataType(r.datatype),
            ),
        )

        return spec.CreateTableResponse(id=table_resp.table_id), table_resp.created

    def patch_table(self, r: spec.PatchTableRequest) -> spec.PatchTableResponse:
        table_metadata = self._repo.fetch_metadata_by_name(r.table_name)
        columns_by_name = table_metadata.table_info.columns

        if r.new_table_name is not None and r.new_table_name != r.table_name:
            if self._repo.is_raw_table_name_taken(r.new_table_name):
                raise RuleValidationError(f"table name {r.new_table_name!r} is already in use")

        with self._repo.with_tx():
            if r.description is not None:
                self._repo.update_table_metadata(r.table_name, r.description)
            if r.datatype is not None:
                self._repo.update_table_datatype(r.table_name, r.datatype)
            if r.status is not None:
                self._repo.update_table_status(r.table_name, r.status)

            for column_name, column_spec in r.columns.items():
                if column_name not in columns_by_name:
                    raise NotFoundError("column", column_name)

                column_metadata = columns_by_name[column_name]
                if column_spec.ucd is not None:
                    column_metadata.ucd = column_spec.ucd
                if column_spec.unit is not None:
                    column_metadata.unit = get_unit(column_spec.unit).to_string()
                if column_spec.description is not None:
                    column_metadata.description = column_spec.description
                if column_spec.ucd is not None or column_spec.unit is not None or column_spec.description is not None:
                    self._repo.update_column_metadata(r.table_name, column_metadata)

            if r.new_table_name is not None and r.new_table_name != r.table_name:
                self._repo.rename_raw_table(r.table_name, r.new_table_name)

        return spec.PatchTableResponse()

    def add_data(self, r: spec.AddDataRequest) -> spec.AddDataResponse:
        data_df = pandas.DataFrame.from_records(r.data)
        data_df[repository.INTERNAL_ID_COLUMN_NAME] = data_df.apply(_get_hash_func(r.table_name), axis=1)
        data_df = data_df.drop_duplicates(subset=repository.INTERNAL_ID_COLUMN_NAME, keep="last")

        with self._repo.with_tx():
            errgr = concurrency.ErrorGroup()
            errgr.run(
                self._repo.insert_raw_data,
                model.Layer0RawData(
                    table_name=r.table_name,
                    data=data_df,
                ),
            )
            errgr.run(
                self._repo.register_records,
                r.table_name,
                record_ids=data_df[repository.INTERNAL_ID_COLUMN_NAME].tolist(),
            )

            errgr.wait()

        return spec.AddDataResponse()

    def get_table_list(self, r: spec.GetTableListRequest) -> spec.GetTableListResponse:
        items = self._repo.search_tables(r.query, r.page_size, r.page, r.statuses)
        cached_tables = self.table_stats_cache.get().tables
        empty_progress = spec.TableProgress(
            total_records=0,
            unprocessed=0,
            pending_triage=0,
            resolved_unsubmitted=0,
            submitted=0,
            catalogs={},
        )
        tables: list[spec.TableListItem] = []
        for item in items:
            progress = cached_tables.get(item.table_name) or empty_progress
            tables.append(
                spec.TableListItem(
                    name=item.table_name,
                    description=item.description,
                    num_entries=progress.total_records,
                    num_fields=item.num_fields,
                    modification_dt=item.modification_dt,
                    bibcode=item.bibcode,
                    status=item.status,
                    progress=progress,
                )
            )
        return spec.GetTableListResponse(tables=tables)

    def get_table(self, r: spec.GetTableRequest) -> spec.GetTableResponse:
        meta = self._repo.fetch_metadata_by_name(r.table_name)

        bibliography = self._repo.get_source_by_id(meta.bibliography_id)

        if meta.table_id is None:
            raise RuntimeError(f"Table {r.table_name} has no ID")

        metadata = {
            "datatype": meta.datatype,
            "status": meta.status,
            "modification_dt": meta.modification_dt,
        }

        progress = self.table_stats_cache.get().tables.get(r.table_name)
        if progress is None:
            fallback = self._repo.get_table_progress([r.table_name])
            table_progress = fallback.get(r.table_name)
            if table_progress is None:
                table_progress = model.TableProgress(
                    total_records=0,
                    unprocessed=0,
                    pending_triage=0,
                    resolved_unsubmitted=0,
                    submitted=0,
                    catalogs={},
                )
            progress = table_stats.table_progress_to_presentation(table_progress)

        return spec.GetTableResponse(
            id=meta.table_id,
            description=meta.table_info.description or "",
            column_info=_column_info_to_presentation(meta.table_info.columns.values()),
            meta=metadata,
            bibliography=_bibliography_to_presentation(bibliography),
            progress=progress,
        )

    def get_records(self, r: spec.GetRecordsRequest) -> spec.GetRecordsResponse:
        has_pgc = None
        if r.upload_status == spec.UploadStatus.UPLOADED:
            has_pgc = True
        elif r.upload_status == spec.UploadStatus.PENDING:
            has_pgc = False

        triage_filter = r.triage_status.value if r.triage_status is not None else None
        errgr = concurrency.ErrorGroup()
        records_task = errgr.run(
            self._repo.fetch_records,
            table_name=r.table_name,
            limit=r.page_size,
            row_offset=r.page * r.page_size,
            order_direction="asc",
            has_pgc=has_pgc,
            pgc_value=r.pgc,
            triage_status=triage_filter,
        )
        schema_task = errgr.run(
            self._repo.get_table_metadata,
            repository.RAWDATA_SCHEMA,
            r.table_name,
        )
        designation_schema_task = errgr.run(
            self._repo.get_table_metadata,
            "designation",
            "data",
        )
        icrs_schema_task = errgr.run(
            self._repo.get_table_metadata,
            "icrs",
            "data",
        )
        nature_schema_task = errgr.run(
            self._repo.get_table_metadata,
            "nature",
            "data",
        )
        nature_object_types_task = errgr.run(
            self._repo.get_nature_object_types,
        )
        errgr.wait()

        raw_records = records_task.result()
        schema_info = schema_task.result()
        designation_schema = designation_schema_task.result()
        icrs_schema = icrs_schema_task.result()
        nature_schema = nature_schema_task.result()
        nature_object_types_rows = nature_object_types_task.result()
        nature_object_types = {row["type_name"]: row["description"] for row in nature_object_types_rows}

        record_ids = [rec.id for rec in raw_records]

        catalog_errgr = concurrency.ErrorGroup()
        designation_task = catalog_errgr.run(
            self._repo.get_designation_records,
            record_ids,
        )
        icrs_task = catalog_errgr.run(
            self._repo.get_icrs_records,
            record_ids,
        )
        redshift_task = catalog_errgr.run(
            self._repo.get_redshift_records,
            record_ids,
        )
        nature_task = catalog_errgr.run(
            self._repo.get_nature_records,
            record_ids,
        )
        catalog_errgr.wait()
        designation_records = designation_task.result()
        icrs_records = icrs_task.result()
        redshift_records = redshift_task.result()
        nature_records = nature_task.result()

        records_list = [
            spec.Record(
                id=rec.id,
                original_data=rec.original_data,
                pgc=rec.pgc,
                crossmatch=spec.RecordCrossmatchInfo(
                    triage_status=spec.CrossmatchTriageStatus(rec.triage_status),
                    candidates=[spec.RecordCrossmatchCandidate(pgc=p) for p in rec.crossmatch_candidates],
                ),
                catalogs=spec.RecordCatalogValues(
                    designation=spec.RecordDesignationCatalog(name=dr.design) if dr else None,
                    icrs=spec.RecordICRSCatalog(
                        ra=ir.ra,
                        ra_error=ir.e_ra,
                        dec=ir.dec,
                        dec_error=ir.e_dec,
                    )
                    if ir
                    else None,
                    redshift=spec.RecordRedshiftCatalog(
                        z=astronomy.heliocentric_cz_to_z(rr.cz * u.Unit("km/s")),
                        z_error=astronomy.heliocentric_cz_to_z(rr.e_cz * u.Unit("km/s")),
                    )
                    if rr
                    else None,
                    nature=spec.RecordNatureCatalog(type_name=nr.type_name) if nr else None,
                ),
            )
            for rec, dr, ir, rr, nr in zip(
                raw_records,
                designation_records,
                icrs_records,
                redshift_records,
                nature_records,
                strict=True,
            )
        ]

        description_data: dict[str, str] = {}
        unit_data: dict[str, str] = {}
        ucd_data: dict[str, str] = {}
        for col in schema_info.columns.values():
            if col.name in FORBIDDEN_COLUMN_NAMES:
                continue
            if col.description is not None:
                description_data[col.name] = col.description
            if col.unit is not None:
                unit_data[col.name] = col.unit
            if col.ucd is not None:
                ucd_data[col.name] = col.ucd

        catalog_schema = _build_catalog_schema(
            designation_schema,
            icrs_schema,
            nature_schema,
            nature_object_types,
        )
        record_schema = spec.RecordSchema(
            original_data=spec.RecordOriginalDataSchema(
                description=description_data,
                ucd=ucd_data,
                unit=unit_data,
            ),
            catalogs=catalog_schema,
        )
        return spec.GetRecordsResponse(records=records_list, schema=record_schema)


def _bibliography_to_presentation(bib: model.Bibliography) -> spec.Bibliography:
    return spec.Bibliography(title=bib.title, authors=bib.author, year=bib.year, bibcode=bib.code)


def _column_info_to_presentation(columns: Iterable[postgres.ColumnInfo]) -> list[spec.ColumnDescription]:
    res = []

    for col in sorted(columns, key=lambda c: c.name):
        if col.name in FORBIDDEN_COLUMN_NAMES:
            continue

        res.append(
            spec.ColumnDescription(
                name=col.name,
                data_type=spec.DatatypeEnum[col.data_type],
                ucd=col.ucd,
                unit=col.unit,
                description=col.description,
            )
        )

    return res


def _get_hash_func(table_name: str) -> Callable[[pandas.Series], str]:
    def _compute_hash(row: pandas.Series) -> str:
        data = []

        for key, val in dict(row).items():
            data.append([key, val])

        data = sorted(data, key=lambda t: t[0])
        data_string = json.dumps(data, separators=(",", ":"))

        return _hashfunc(f"{table_name}_{data_string}")

    return _compute_hash


def _hashfunc(string: str) -> str:
    return str(uuid.UUID(hashlib.md5(string.encode("utf-8"), usedforsecurity=False).hexdigest()))


def ensure_source_id(repo: repository.Repository, ads_client: ads.ADSClass, code: str) -> int:
    if not regex.match(BIBCODE_REGEX, code):
        try:
            entry_id = repo.get_source_entry(code).id
        except RuntimeError as e:
            raise RuleValidationError(f"source with code '{code}' not found") from e

        return entry_id

    try:
        publication = ads_client.query_simple(f'bibcode:"{code}"')[0]
    except RuntimeError as e:
        raise RuleValidationError(f"bibcode '{code}' not found in ADS") from e

    title = publication["title"][0]
    authors = list(publication["author"])
    # for some reason ADS sends both 2016-00-00 and 2016-02-00 formats.
    # since we do not care about the months, we only take year.
    year = int(str(publication["pubdate"])[:4])

    return repo.create_bibliography(code, year, authors, title)


def get_unit(u: str) -> units.Unit:
    # astropy does not support "log" as a function on unit, so we need to explicitly change it to "dex".
    # this might cause issues if the unit is a log-log unit or "10 * log" since we will only change the first log.
    # however, as of writing, astropy does not support such units anyway.
    if u.startswith("log(") and u.endswith(")"):
        u = f"dex({u[4:-1]})"

    try:
        return units.Unit(u)
    except ValueError:
        raise RuleValidationError(f"unknown unit: '{u}'") from None


def domain_descriptions_to_data(
    table_name: str,
    columns: list[spec.ColumnDescription],
    description: str | None = None,
) -> postgres.TableInfo:
    result: dict[str, postgres.ColumnInfo] = {
        repository.INTERNAL_ID_COLUMN_NAME: postgres.ColumnInfo(
            name=repository.INTERNAL_ID_COLUMN_NAME,
            data_type=mapping.TYPE_TEXT,
            description=None,
            unit=None,
            ucd=None,
            not_null=True,
        )
    }

    for col in columns:
        data_type = col.data_type.strip()
        unit = None
        col_description = col.description

        if data_type not in mapping.type_map:
            raise RuleValidationError(f"unknown type of data: '{col.data_type}'")

        if col.unit is not None:
            try:
                unit = get_unit(col.unit).to_string()
            except RuleValidationError:
                logger.error("Failed to parse unit, ignoring", unit=col.unit, column=col.name)
                col_description = f"{col_description or ''} (unit {col.unit})".lstrip()

        if ucd is not None and not ucd.check_ucd(col.ucd, check_controlled_vocabulary=False):
            raise RuleValidationError(f"invalid or unknown UCD: {col.ucd}")

        if col.name in result:
            raise RuleValidationError(f"duplicate column name: {col.name}")

        result[col.name] = postgres.ColumnInfo(
            name=col.name,
            data_type=mapping.type_map[data_type],
            unit=unit,
            ucd=col.ucd,
            description=col_description,
        )

    return postgres.TableInfo(
        schema=repository.RAWDATA_SCHEMA,
        name=table_name,
        description=description,
        columns=result,
        primary_keys={repository.INTERNAL_ID_COLUMN_NAME},
    )
