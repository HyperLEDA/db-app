import hashlib
import json
import uuid
from collections.abc import Callable

import astropy.io.votable.ucd as ucd
import pandas
import regex
from astropy import units
from astroquery import nasa_ads as ads

from app.data import model, repositories
from app.lib import clients
from app.lib.storage import enums, mapping
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.presentation import adminapi

BIBCODE_REGEX = "^([0-9]{4}[A-Za-z.&]{5}[A-Za-z0-9.]{4}[AELPQ-Z0-9.][0-9.]{4}[A-Z])$"

FORBIDDEN_COLUMN_NAMES = {repositories.INTERNAL_ID_COLUMN_NAME}


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

        return adminapi.CreateTableResponse(table_resp.table_id), table_resp.created

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
            self.layer0_repo.insert_raw_data(
                model.Layer0RawData(
                    table_id=r.table_id,
                    data=data_df,
                ),
            )

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
                        enrichment=config.enrichment or {},
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
