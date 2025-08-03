import pandas
import structlog

from app.data import model
from app.data.repositories.layer2 import filters, params
from app.data.repositories.layer2.repository import Layer2Repository
from experiments.entities import CrossIdentificationResult

logger = structlog.get_logger()


def cross_identify_objects(
    fast_objects: pandas.DataFrame,
    layer2_repo: Layer2Repository,
    search_radius_degrees: float = 0.1,
) -> dict[str, CrossIdentificationResult]:
    """
    Perform cross-identification of objects from fast_objects with objects in the HyperLEDA database.

    Args:
        fast_objects: DataFrame containing objects to cross-identify
        layer2_repo: Layer2Repository instance for database queries
        search_radius_degrees: Search radius in degrees for coordinate matching

    Returns:
        Dictionary mapping object IDs to cross-identification results
    """
    results: dict[str, CrossIdentificationResult] = {}

    ra_column = None
    dec_column = None

    for ra_name in ["ra", "RAJ2000", "RA", "ra_deg"]:
        if ra_name in fast_objects.columns:
            ra_column = ra_name
            break

    for dec_name in ["dec", "DEJ2000", "DEC", "dec_deg"]:
        if dec_name in fast_objects.columns:
            dec_column = dec_name
            break

    if ra_column is None or dec_column is None:
        available_columns = list(fast_objects.columns)
        raise ValueError(f"Could not find RA/Dec columns. Available columns: {available_columns}")

    logger.info(f"Using columns: {ra_column} for RA, {dec_column} for Dec")

    batch_size = 1000
    total_objects = len(fast_objects)

    for batch_start in range(0, total_objects, batch_size):
        batch_end = min(batch_start + batch_size, total_objects)
        batch_objects = fast_objects.iloc[batch_start:batch_end]

        logger.info(f"Processing batch {batch_start // batch_size + 1}, objects {batch_start + 1}-{batch_end}")

        search_types: dict[str, filters.Filter] = {"icrs": filters.ICRSCoordinatesInRadiusFilter(search_radius_degrees)}

        search_params = {}
        for idx, (_, obj) in enumerate(batch_objects.iterrows()):
            object_id = f"obj_{batch_start + idx}"
            search_params[object_id] = params.ICRSSearchParams(ra=obj[ra_column], dec=obj[dec_column])

        batch_results = layer2_repo.query_batch(
            catalogs=[model.RawCatalog.ICRS],
            search_types=search_types,
            search_params=search_params,
            limit=1000,
            offset=0,
        )

        for idx, (_, obj) in enumerate(batch_objects.iterrows()):
            object_id = f"obj_{batch_start + idx}"
            matched_objects = batch_results.get(object_id, [])

            if len(matched_objects) == 0:
                results[object_id] = CrossIdentificationResult(status="new")
            elif len(matched_objects) == 1:
                results[object_id] = CrossIdentificationResult(status="existing", pgc_numbers=[matched_objects[0].pgc])
            else:
                pgc_numbers = [obj.pgc for obj in matched_objects]
                results[object_id] = CrossIdentificationResult(status="collision", pgc_numbers=pgc_numbers)

    return results
