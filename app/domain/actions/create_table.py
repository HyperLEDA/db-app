from datetime import datetime, timezone

import astropy.io.votable.ucd as ucd
import regex
from astropy import units
from astroquery import nasa_ads as ads

from app import commands, schema
from app.data import interface
from app.data import model as data_model
from app.lib.storage import enums, mapping
from app.lib.web.errors import RuleValidationError

BIBCODE_REGEX = "^([0-9]{4}[A-Za-z.&]{5}[A-Za-z0-9.]{4}[AELPQ-Z0-9.][0-9.]{4}[A-Z])$"
INTERNAL_ID_COLUMN_NAME = "hyperleda_internal_id"

FORBIDDEN_COLUMN_NAMES = {INTERNAL_ID_COLUMN_NAME}


def create_table(
    depot: commands.Depot,
    r: schema.CreateTableRequest,
) -> tuple[schema.CreateTableResponse, bool]:
    source_id = get_source_id(depot.common_repo, depot.clients.ads, r.bibcode)

    for col in r.columns:
        if col.name in FORBIDDEN_COLUMN_NAMES:
            raise RuleValidationError(f"{col} is a reserved column name for internal storage")

    columns = domain_descriptions_to_data(r.columns)

    with depot.layer0_repo.with_tx() as tx:
        table_resp = depot.layer0_repo.create_table(
            data_model.Layer0Creation(
                table_name=r.table_name,
                column_descriptions=columns,
                bibliography_id=source_id,
                datatype=enums.DataType(r.datatype),
                comment=r.description,
            ),
            tx=tx,
        )

    return schema.CreateTableResponse(table_resp.table_id), table_resp.created


def get_source_id(repo: interface.CommonRepository, ads_client: ads.ADSClass, code: str) -> int:
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
    year = datetime.strptime(publication["pubdate"], "%Y-%m-00").astimezone(timezone.utc).year

    return repo.create_bibliography(code, year, authors, title)


def domain_descriptions_to_data(columns: list[schema.ColumnDescription]) -> list[data_model.ColumnDescription]:
    result = [
        data_model.ColumnDescription(
            name=INTERNAL_ID_COLUMN_NAME,
            data_type=mapping.TYPE_TEXT,
            is_primary_key=True,
        )
    ]

    for col in columns:
        data_type = col.data_type.strip()
        unit = col.unit

        if data_type not in mapping.type_map:
            raise RuleValidationError(f"unknown type of data: '{col.data_type}'")

        if col.unit is not None:
            try:
                unit = units.Unit(col.unit).to_string()
            except ValueError:
                raise RuleValidationError(f"unknown unit: '{col.unit}'") from None

        if ucd is not None and not ucd.check_ucd(col.ucd, check_controlled_vocabulary=True):
            raise RuleValidationError(f"invalid or unknown UCD: {col.ucd}")

        result.append(
            data_model.ColumnDescription(
                name=col.name,
                data_type=mapping.type_map[data_type],
                unit=unit,
                ucd=col.ucd,
                description=col.description,
            )
        )

    return result
