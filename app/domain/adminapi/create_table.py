from datetime import UTC, datetime

import astropy.io.votable.ucd as ucd
import regex
from astropy import units
from astroquery import nasa_ads as ads

from app import entities, schema
from app.commands.adminapi import depot
from app.data import repositories
from app.domain import converters
from app.lib.storage import enums, mapping
from app.lib.web import errors
from app.lib.web.errors import RuleValidationError

BIBCODE_REGEX = "^([0-9]{4}[A-Za-z.&]{5}[A-Za-z0-9.]{4}[AELPQ-Z0-9.][0-9.]{4}[A-Z])$"

FORBIDDEN_COLUMN_NAMES = {repositories.INTERNAL_ID_COLUMN_NAME}


def create_table(
    dpt: depot.Depot,
    r: schema.CreateTableRequest,
) -> tuple[schema.CreateTableResponse, bool]:
    source_id = get_source_id(dpt.common_repo, dpt.clients.ads, r.bibcode)

    r.table_name = sanitize_name(r.table_name)

    for col in r.columns:
        if col.name in FORBIDDEN_COLUMN_NAMES:
            raise RuleValidationError(f"{col} is a reserved column name")

    columns = domain_descriptions_to_data(r.columns)
    validate_columns(columns)

    table_resp = dpt.layer0_repo.create_table(
        entities.Layer0Creation(
            table_name=r.table_name,
            column_descriptions=columns,
            bibliography_id=source_id,
            datatype=enums.DataType(r.datatype),
            comment=r.description,
        ),
    )

    return schema.CreateTableResponse(table_resp.table_id), table_resp.created


def sanitize_name(name: str) -> str:
    return name.replace(" ", "_").replace("-", "_")


def validate_columns(columns: list[entities.ColumnDescription]):
    converter = converters.CompositeConverter(
        converters.NameConverter(),
        converters.ICRSConverter(),
    )

    try:
        converter.parse_columns(columns)
    except converters.ConverterError as e:
        raise errors.RuleValidationError(f"Unable to parse the columns: {str(e)}") from e


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


def domain_descriptions_to_data(columns: list[schema.ColumnDescription]) -> list[entities.ColumnDescription]:
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
