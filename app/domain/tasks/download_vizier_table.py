import random
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
TABLE_NAMING_FORMAT = "data_{table_id}"


def get_timeout_trace_func(start: float, timeout: float):
    def trace_function(frame, event, arg):
        if time.time() - start > timeout:
            raise TimeoutError("Timeout")

        return trace_function

    return trace_function


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

    bad_fields = [field for field in catalog.columns if "-" in field]
    for bad_field in bad_fields:
        catalog[bad_field.replace("-", "_")] = catalog[bad_field]
        catalog.remove_column(bad_field)

    field: str
    for field in catalog.columns:
        if isinstance(catalog[field], ma.MaskedArray):
            if catalog[field].dtype == np.int16:
                catalog[field] = catalog[field].filled(0)
            else:
                catalog[field] = catalog[field].filled(np.nan)

    fields = []
    for field, field_meta in catalog.columns.items():
        t = mapping.get_type_from_dtype(field_meta.dtype)
        field = field.replace("-", "_")
        fields.append((field, t))

    # TODO: make this a reasonable algorithm
    table_id = random.randint(0, 2000000000)
    with layer0.with_tx() as tx:
        layer0.create_table(RAWDATA_SCHEMA, TABLE_NAMING_FORMAT.format(table_id), fields, tx)

        raw_data = list(catalog)
        layer0.insert_raw_data(RAWDATA_SCHEMA, TABLE_NAMING_FORMAT.format(table_id), raw_data, tx)
