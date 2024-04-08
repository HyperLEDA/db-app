import sys
import time
from dataclasses import dataclass

import numpy as np
import structlog
from astropy import table
from astroquery.vizier import VizierClass
from numpy import ma

from app.data import repositories
from app.lib.exceptions import new_not_found_error
from app.lib.storage import mapping, postgres

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
    layer0 = repositories.Layer0Repository(storage, logger)
    table_name = construct_table_name(params.table_id)

    if layer0.table_exists(RAWDATA_SCHEMA, table_name):
        logger.warn(f"table '{RAWDATA_SCHEMA}.{table_name}' already exists, skipping download")
        return

    vizier_client = VizierClass()
    vizier_client.ROW_LIMIT = -1
    vizier_client.TIMEOUT = 30

    timeout_handler = get_timeout_trace_func(
        time.time(),
        vizier_client.TIMEOUT,
    )
    sys.settrace(timeout_handler)

    try:
        logger.info("querying Vizier")
        catalogs = vizier_client.get_catalogs(params.catalog_id)
    # TODO: probably should choose some more specific exception
    except Exception as e:
        raise TimeoutError(
            "Downloading from Vizier took too long, cancelling. To download a big table ask HyperLeda team for help."
        ) from e
    finally:
        sys.settrace(None)

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
        raise new_not_found_error("catalog or table you requested was not found")

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
        fields.append((field, t))

    with layer0.with_tx() as tx:
        layer0.create_table(RAWDATA_SCHEMA, table_name, fields, tx)

        raw_data = list(catalog)
        layer0.insert_raw_data(RAWDATA_SCHEMA, table_name, raw_data, tx)
