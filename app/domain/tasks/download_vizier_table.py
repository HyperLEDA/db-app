import time
from dataclasses import dataclass

import numpy as np
import structlog
from astropy import table
from astroquery import vizier
from numpy import ma

from app import entities
from app.data import repositories
from app.lib.storage import enums, mapping, postgres

RAWDATA_SCHEMA = "rawdata"
TABLE_NAMING_FORMAT = "data_vizier_{table_id}"


def get_timeout_trace_func(start: float, timeout: float):
    def trace_function(frame, event, arg):
        if time.time() - start > timeout:
            raise TimeoutError("Timeout")

        return trace_function

    return trace_function


BAD_SYMBOLS = {
    "-": "_",
    "/": "_",
}


def replace_dict(string: str, symbols: dict[str, str]) -> str:
    """
    Works similarly to `str.replace` but for dictionary of symbols.
    """
    for old_symbol, new_symbol in symbols.items():
        string = string.replace(old_symbol, new_symbol)

    return string


def construct_table_name(original_name: str) -> str:
    new_name = replace_dict(original_name, BAD_SYMBOLS)

    return TABLE_NAMING_FORMAT.format(table_id=new_name)


@dataclass
class DownloadVizierTableParams:
    catalog_id: str
    table_id: str


def download_vizier_table(
    storage: postgres.PgStorage,
    params: DownloadVizierTableParams,
    logger: structlog.stdlib.BoundLogger,
):
    common = repositories.CommonRepository(storage, logger)

    layer0 = repositories.Layer0Repository(storage, logger)
    table_name = construct_table_name(params.table_id)

    table_id, ok = layer0.get_table_id(table_name)
    if ok:
        logger.warn(f"table '{RAWDATA_SCHEMA}.{table_name}' already exists, skipping download")
        return

    vizier_client = vizier.VizierClass()
    vizier_client.ROW_LIMIT = -1
    vizier_client.TIMEOUT = 30

    # timeout_handler = get_timeout_trace_func(
    #     time.time(),
    #     vizier_client.TIMEOUT,
    # )
    # sys.settrace(timeout_handler)

    try:
        logger.info("querying Vizier")
        catalogs = vizier_client.get_catalogs(params.catalog_id)
    # TODO: probably should choose some more specific exception
    except Exception as e:
        raise TimeoutError(
            "Downloading from Vizier took too long, cancelling. To download a big table ask HyperLeda team for help."
        ) from e
    finally:
        pass
        # sys.settrace(None)

    catalog: table.Table | None = None
    for curr_catalog in catalogs:
        try:
            name = curr_catalog.meta["name"]
        except KeyError:
            continue

        if name != params.table_id:
            continue

        catalog = curr_catalog
        break

    if catalog is None:
        raise RuntimeError("catalog or table you requested was not found")

    field: str
    for field in catalog.colnames:
        new_field = replace_dict(field, BAD_SYMBOLS)
        if field != new_field:
            catalog[new_field] = catalog[field]
            catalog.remove_column(field)

        # TODO: move this validation to separate function
        if isinstance(catalog[new_field], ma.MaskedArray):
            if catalog[new_field].dtype == np.int16:
                catalog[new_field] = catalog[new_field].filled(0)
            else:
                catalog[new_field] = catalog[new_field].filled(np.nan)

    fields = []
    for field, field_meta in catalog.columns.items():
        t = mapping.get_type_from_dtype(field_meta.dtype)
        fields.append(
            entities.ColumnDescription(
                name=field,
                data_type=t,
                unit=field_meta.unit,
                description=field_meta.description,
            )
        )

    with layer0.with_tx():
        try:
            description = catalog.meta["description"]
        except KeyError:
            description = ""

        # TODO: parse real bibliographic data from vizier response
        bib_id = common.create_bibliography(
            code="2024arXiv240403522G",
            year=2024,
            authors=["Pović, Mirjana"],
            title="The Lockman-SpReSO project. Galactic flows in a sample of far-infrared galaxies",
        )

        table_resp = layer0.create_table(
            entities.Layer0Creation(
                table_name,
                fields,
                bib_id,
                # TODO: obtain that info from vizier
                enums.DataType.REGULAR,
                comment=description,
            ),
        )

        layer0.insert_raw_data(entities.Layer0RawData(table_resp.table_id, catalog.to_pandas()))
