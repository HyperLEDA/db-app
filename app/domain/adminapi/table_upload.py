import hashlib
import json
import uuid
from collections.abc import Callable

import astropy.io.votable.ucd as ucd
import pandas
import regex
import structlog
from astropy import units
from astroquery import nasa_ads as ads

from app.data import model, repositories
from app.domain import homogenization
from app.lib import clients, concurrency
from app.lib.storage import enums, mapping
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.presentation import adminapi

BIBCODE_REGEX = "^([0-9]{4}[A-Za-z.&]{5}[A-Za-z0-9.]{4}[AELPQ-Z0-9.][0-9.]{4}[A-Z])$"

FORBIDDEN_COLUMN_NAMES = {repositories.INTERNAL_ID_COLUMN_NAME}

logger = structlog.stdlib.get_logger()


class TableUploadManager:
    def __init__(
        self,
        common_repo: repositories.CommonRepository,
        layer0_repo: repositories.Layer0Repository,
        clients: clients.Clients,
    ) -> None:
        self.common_repo = common_repo
        self.layer0_repo = layer0_repo
        self.clients = clients

    def create_table(self, r: adminapi.CreateTableRequest) -> tuple[adminapi.CreateTableResponse, bool]:
        source_id = get_source_id(self.common_repo, self.clients.ads, r.bibcode)

        for col in r.columns:
            if col.name in FORBIDDEN_COLUMN_NAMES:
                raise RuleValidationError(f"{col} is a reserved column name")

        columns = domain_descriptions_to_data(r.columns)

        table_resp = self.layer0_repo.create_table(
            model.Layer0TableMeta(
                table_name=r.table_name,
                column_descriptions=columns,
                bibliography_id=source_id,
                datatype=enums.DataType(r.datatype),
                description=r.description,
            ),
        )

        return adminapi.CreateTableResponse(id=table_resp.table_id), table_resp.created

    def patch_table(self, r: adminapi.PatchTableRequest) -> adminapi.PatchTableResponse:
        table_metadata = self.layer0_repo.fetch_metadata_by_name(r.table_name)
        columns_by_id = {col.name: col for col in table_metadata.column_descriptions}

        with self.layer0_repo.with_tx():
            for action in r.actions:
                if isinstance(action, adminapi.PatchTableActionTypeChangeUCD):
                    column_metadata = columns_by_id[action.column]
                    column_metadata.ucd = action.ucd

                    self.layer0_repo.update_column_metadata(r.table_name, column_metadata)
                elif isinstance(action, adminapi.PatchTableActionTypeChangeUnit):
                    column_metadata = columns_by_id[action.column]
                    column_metadata.unit = units.Unit(action.unit)

                    self.layer0_repo.update_column_metadata(r.table_name, column_metadata)
                else:
                    raise RuntimeError(f"unknown action type: {action}")

        return adminapi.PatchTableResponse()

    def add_data(self, r: adminapi.AddDataRequest) -> adminapi.AddDataResponse:
        data_df = pandas.DataFrame.from_records(r.data)
        data_df[repositories.INTERNAL_ID_COLUMN_NAME] = data_df.apply(_get_hash_func(r.table_id), axis=1)
        data_df = data_df.drop_duplicates(subset=repositories.INTERNAL_ID_COLUMN_NAME, keep="last")

        with self.layer0_repo.with_tx():
            errgr = concurrency.ErrorGroup()
            errgr.run(
                self.layer0_repo.insert_raw_data,
                model.Layer0RawData(
                    table_id=r.table_id,
                    data=data_df,
                ),
            )
            errgr.run(
                self.layer0_repo.upsert_objects,
                r.table_id,
                objects=[
                    model.Layer0Object(object_id=object_id, data=[])
                    for object_id in data_df[repositories.INTERNAL_ID_COLUMN_NAME].tolist()
                ],
            )

            errgr.wait()

        return adminapi.AddDataResponse()

    def create_marking(self, r: adminapi.CreateMarkingRequest) -> adminapi.CreateMarkingResponse:
        rules = []
        params = []

        try:
            meta = self.layer0_repo.fetch_metadata_by_name(r.table_name)
        except RuntimeError as e:
            raise NotFoundError("table", r.table_name) from e

        columns = set()

        for col in meta.column_descriptions:
            columns.add(col.name)

        for rule in r.catalogs:
            for parameter, config in rule.parameters.items():
                if config.column_name not in columns:
                    raise NotFoundError("column", config.column_name, f"table '{r.table_name}'")

                filters = {
                    "table_name": r.table_name,
                    "column_name": config.column_name,
                }

                rules.append(
                    model.HomogenizationRule(
                        catalog=rule.name,
                        parameter=parameter,
                        filters=filters,
                        key=rule.key or "",
                    )
                )

            if rule.additional_params is None:
                continue

            curr_params = {}
            for param, value in rule.additional_params.items():
                curr_params[param] = value

            params.append(
                model.HomogenizationParams(
                    catalog=rule.name,
                    key=rule.key or "",
                    params=curr_params,
                )
            )

        with self.layer0_repo.with_tx():
            self.layer0_repo.add_homogenization_rules(rules)
            if len(params) > 0:
                self.layer0_repo.add_homogenization_params(params)

        return adminapi.CreateMarkingResponse()

    def get_table(self, r: adminapi.GetTableRequest) -> adminapi.GetTableResponse:
        meta = self.layer0_repo.fetch_metadata_by_name(r.table_name)

        bibliography = self.common_repo.get_source_by_id(meta.bibliography_id)

        if meta.table_id is None:
            raise RuntimeError(f"Table {r.table_name} has no ID")

        table_stats = self.layer0_repo.get_table_statistics(meta.table_id)
        rows_num = table_stats.total_original_rows
        metadata = {"datatype": meta.datatype, "modification_dt": meta.modification_dt}

        hom = get_homogenization(self.layer0_repo, meta)
        mapping = hom.get_column_mapping()

        statistics = None
        if table_stats.statuses:
            statistics = table_stats.statuses

        return adminapi.GetTableResponse(
            id=meta.table_id,
            description=meta.description or "",
            column_info=_column_description_to_presentation(meta.column_descriptions),
            rows_num=rows_num,
            meta=metadata,
            bibliography=_bibliography_to_presentation(bibliography),
            marking_rules=[
                adminapi.MarkingRule(catalog=catalog.value, key=key, columns=data)
                for ((catalog, key), data) in mapping.items()
            ],
            statistics=statistics,
        )


def new_rule(rule: model.HomogenizationRule) -> homogenization.Rule:
    return homogenization.Rule(
        model.RawCatalog(rule.catalog),
        rule.parameter,
        homogenization.parse_filters(rule.filters),
        rule.key or "",
        rule.priority or 2**32,
    )


def new_params(params: model.HomogenizationParams) -> homogenization.Params:
    return homogenization.Params(model.RawCatalog(params.catalog), params.key, params.params)


def get_homogenization(
    repo: repositories.Layer0Repository,
    metadata: model.Layer0TableMeta,
    **kwargs,
) -> homogenization.Homogenization:
    db_rules = repo.get_homogenization_rules()
    db_params = repo.get_homogenization_params()

    rules = [new_rule(rule) for rule in db_rules]
    params = [new_params(param) for param in db_params]

    return homogenization.get_homogenization(rules, params, metadata, **kwargs)


def _bibliography_to_presentation(bib: model.Bibliography) -> adminapi.Bibliography:
    return adminapi.Bibliography(title=bib.title, authors=bib.author, year=bib.year, bibcode=bib.code)


def _column_description_to_presentation(columns: list[model.ColumnDescription]) -> list[adminapi.ColumnDescription]:
    res = []

    for col in columns:
        if col.name in FORBIDDEN_COLUMN_NAMES:
            continue

        res.append(
            adminapi.ColumnDescription(
                name=col.name,
                data_type=adminapi.DatatypeEnum[col.data_type],
                ucd=col.ucd,
                unit=col.unit.to_string() if col.unit is not None else None,
                description=col.description,
            )
        )

    return res


def _get_hash_func(table_id: int) -> Callable[[pandas.Series], str]:
    def _compute_hash(row: pandas.Series) -> str:
        """
        This function applies special algorithm to an iterable to compute stable hash.
        It ensures that values are sorted and that spacing is not an issue.
        """
        data = []

        for key, val in dict(row).items():
            data.append([key, val])

        data = sorted(data, key=lambda t: t[0])
        data_string = json.dumps(data, separators=(",", ":"))

        return _hashfunc(f"{table_id}_{data_string}")

    return _compute_hash


def _hashfunc(string: str) -> str:
    return str(uuid.UUID(hashlib.md5(string.encode("utf-8"), usedforsecurity=False).hexdigest()))


def get_source_id(repo: repositories.CommonRepository, ads_client: ads.ADSClass, code: str) -> int:
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
    # astropy does not support "log" as a function on unit, so we need to explicitly change it do "dex".
    # this might cause issues if the unit is a log-log unit or "10 * log" since we will only change the first log.
    # however, as of writing, astropy does not support such units anyway.
    if u.startswith("log(") and u.endswith(")"):
        u = f"dex({u[4:-1]})"

    try:
        return units.Unit(u)
    except ValueError:
        raise RuleValidationError(f"unknown unit: '{u}'") from None


def domain_descriptions_to_data(columns: list[adminapi.ColumnDescription]) -> list[model.ColumnDescription]:
    result = [
        model.ColumnDescription(
            name=repositories.INTERNAL_ID_COLUMN_NAME,
            data_type=mapping.TYPE_TEXT,
            is_primary_key=True,
        )
    ]

    for col in columns:
        data_type = col.data_type.strip()
        unit = None

        if data_type not in mapping.type_map:
            raise RuleValidationError(f"unknown type of data: '{col.data_type}'")

        if col.unit is not None:
            unit = get_unit(col.unit)

        if ucd is not None and not ucd.check_ucd(col.ucd, check_controlled_vocabulary=False):
            raise RuleValidationError(f"invalid or unknown UCD: {col.ucd}")

        result.append(
            model.ColumnDescription(
                name=col.name,
                data_type=mapping.type_map[data_type],
                unit=unit,
                ucd=col.ucd,
                description=col.description,
            )
        )

    return result
