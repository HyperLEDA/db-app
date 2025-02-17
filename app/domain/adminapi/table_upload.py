import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import astropy.io.votable.ucd as ucd
import pandas
import regex
from astropy import units
from astroquery import nasa_ads as ads

from app import entities
from app.data import repositories
from app.domain import converters
from app.lib import clients
from app.lib.storage import enums, mapping
from app.lib.web.errors import RuleValidationError
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

        r.table_name = sanitize_name(r.table_name)

        for col in r.columns:
            if col.name in FORBIDDEN_COLUMN_NAMES:
                raise RuleValidationError(f"{col} is a reserved column name")

        columns = domain_descriptions_to_data(r.columns)

        table_resp = self.layer0_repo.create_table(
            entities.Layer0Creation(
                table_name=r.table_name,
                column_descriptions=columns,
                bibliography_id=source_id,
                datatype=enums.DataType(r.datatype),
                comment=r.description,
            ),
        )

        return adminapi.CreateTableResponse(table_resp.table_id), table_resp.created

    def validate_table(self, r: adminapi.GetTableValidationRequest) -> adminapi.GetTableValidationResponse:
        table_metadata = self.layer0_repo.fetch_metadata(r.table_id)

        validation_result = validate_columns(table_metadata.column_descriptions)

        return adminapi.GetTableValidationResponse(validations=validation_result)

    def patch_table(self, r: adminapi.PatchTableRequest) -> adminapi.PatchTableResponse:
        table_metadata = self.layer0_repo.fetch_metadata(r.table_id)
        columns_by_id = {col.name: col for col in table_metadata.column_descriptions}

        with self.layer0_repo.with_tx():
            for action in r.actions:
                if isinstance(action, adminapi.PatchTableActionTypeChangeUCD):
                    column_metadata = columns_by_id[action.column]
                    column_metadata.ucd = action.ucd

                    self.layer0_repo.update_column_metadata(r.table_id, column_metadata)
                elif isinstance(action, adminapi.PatchTableActionTypeChangeUnit):
                    column_metadata = columns_by_id[action.column]
                    column_metadata.unit = units.Unit(action.unit)

                    self.layer0_repo.update_column_metadata(r.table_id, column_metadata)
                else:
                    raise RuntimeError(f"unknown action type: {action}")

            self.layer0_repo.update_modification_time(r.table_id)

        return adminapi.PatchTableResponse()

    def add_data(self, r: adminapi.AddDataRequest) -> adminapi.AddDataResponse:
        data_df = pandas.DataFrame.from_records(r.data)
        data_df[repositories.INTERNAL_ID_COLUMN_NAME] = data_df.apply(_get_hash_func(r.table_id), axis=1)
        data_df = data_df.drop_duplicates(subset=repositories.INTERNAL_ID_COLUMN_NAME, keep="last")

        with self.layer0_repo.with_tx():
            self.layer0_repo.insert_raw_data(
                entities.Layer0RawData(
                    table_id=r.table_id,
                    data=data_df,
                ),
            )

        return adminapi.AddDataResponse()


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


def sanitize_name(name: str) -> str:
    return name.replace(" ", "_").replace("-", "_").replace(".", "_")


def validate_columns(columns: list[entities.ColumnDescription]) -> list[adminapi.TableValidation]:
    convs = [
        converters.NameConverter(),
        converters.ICRSConverter(),
        converters.RedshiftConverter(),
    ]

    validations = []
    for converter in convs:
        try:
            converter.parse_columns(columns)
        except converters.ConverterError as e:
            validations.append(adminapi.TableValidation(message=str(e), validator=converter.name()))

    return validations


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
    year = datetime.strptime(publication["pubdate"], "%Y-%m-00").astimezone(UTC).year

    return repo.create_bibliography(code, year, authors, title)


def domain_descriptions_to_data(columns: list[adminapi.ColumnDescription]) -> list[entities.ColumnDescription]:
    result = [
        entities.ColumnDescription(
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
            try:
                unit = units.Unit(col.unit)
            except ValueError:
                raise RuleValidationError(f"unknown unit: '{col.unit}'") from None

        if ucd is not None and not ucd.check_ucd(col.ucd, check_controlled_vocabulary=True):
            raise RuleValidationError(f"invalid or unknown UCD: {col.ucd}")

        result.append(
            entities.ColumnDescription(
                name=col.name,
                data_type=mapping.type_map[data_type],
                unit=unit,
                ucd=col.ucd,
                description=col.description,
            )
        )

    return result
