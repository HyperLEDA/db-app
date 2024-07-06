from datetime import datetime, timezone

import regex
from astroquery import nasa_ads as ads

from app import commands
from app.data import interface
from app.data import model as data_model
from app.domain import model as domain_model
from app.lib.exceptions import new_validation_error
from app.lib.storage import enums, mapping

BIBCODE_REGEX = "^([0-9]{4}[A-Za-z.&]{5}[A-Za-z0-9.]{4}[AELPQ-Z0-9.][0-9.]{4}[A-Z])$"


def get_source_id(repo: interface.CommonRepository, ads_client: ads.ADSClass, code: str) -> int:
    if not regex.match(BIBCODE_REGEX, code):
        try:
            entry_id = repo.get_source_entry(code).id
        except RuntimeError as e:
            raise new_validation_error(f"source with code '{code}' not found") from e

        return entry_id

    try:
        publication = ads_client.query_simple(f'bibcode:"{code}"')[0]
    except RuntimeError as e:
        raise new_validation_error(f"bibcode '{code}' not found in ADS") from e

    title = publication["title"][0]
    authors = list(publication["author"])
    year = datetime.strptime(publication["pubdate"], "%Y-%m-00").astimezone(timezone.utc).year

    return repo.create_bibliography(code, year, authors, title)


def domain_descriptions_to_data(columns: list[domain_model.ColumnDescription]) -> list[data_model.ColumnDescription]:
    result = []

    for col in columns:
        if col.data_type not in mapping.type_map:
            raise new_validation_error(f"unknown type of data: {col.data_type}")

        result.append(
            data_model.ColumnDescription(
                name=col.name, data_type=mapping.type_map[col.data_type], unit=col.unit, description=col.description
            )
        )

    return result


def create_table(depot: commands.Depot, r: domain_model.CreateTableRequest) -> domain_model.CreateTableResponse:
    bibliography_id = get_source_id(depot.common_repo, depot.clients.ads, r.bibcode)
    columns = domain_descriptions_to_data(r.columns)

    with depot.layer0_repo.with_tx() as tx:
        table_id = depot.layer0_repo.create_table(
            data_model.Layer0Creation(
                table_name=r.table_name,
                column_descriptions=columns,
                bibliography_id=bibliography_id,
                datatype=enums.DataType(r.datatype),
                comment=r.description,
            ),
            tx=tx,
        )

    return domain_model.CreateTableResponse(table_id)
