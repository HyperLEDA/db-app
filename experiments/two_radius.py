import pandas
import structlog

from app.data import model
from app.data.repositories.layer2 import filters, params
from app.data.repositories.layer2.repository import Layer2Repository
from experiments.entities import CrossIdentificationResult

logger = structlog.get_logger()


def cross_identify_objects_two_radius(
    fast_objects: pandas.DataFrame,
    layer2_repo: Layer2Repository,
    inner_radius_degrees: float = 0.001,  # 3.6 arcseconds
    outer_radius_degrees: float = 0.01,  # 36 arcseconds
) -> dict[str, CrossIdentificationResult]:
    """
    Perform cross-identification using a two-radius approach for better discrimination.

    Algorithm:
    - If no objects in outer radius → "new"
    - If exactly 1 object in inner radius AND no objects between inner and outer radius → "existing"
    - Otherwise → "collision" with all PGC numbers from outer radius

    Args:
        fast_objects: DataFrame containing objects to cross-identify
        layer2_repo: Layer2Repository instance for database queries
        inner_radius_degrees: Inner radius in degrees for confident matches
        outer_radius_degrees: Outer radius in degrees for candidate search

    Returns:
        Dictionary mapping object IDs to cross-identification results
    """
    results: dict[str, CrossIdentificationResult] = {}

    # Check if fast_objects has required columns and map them to standard names
    ra_column = None
    dec_column = None

    # Try different possible column names for coordinates
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

    logger.info(f"Using two-radius approach: inner={inner_radius_degrees:.6f}°, outer={outer_radius_degrees:.6f}°")
    logger.info(f"Using columns: {ra_column} for RA, {dec_column} for Dec")

    # Process objects in batches
    batch_size = 1000
    total_objects = len(fast_objects)

    for batch_start in range(0, total_objects, batch_size):
        batch_end = min(batch_start + batch_size, total_objects)
        batch_objects = fast_objects.iloc[batch_start:batch_end]

        logger.info(f"Processing batch {batch_start // batch_size + 1}, objects {batch_start + 1}-{batch_end}")

        # Query for outer radius matches (this will include inner radius matches too)
        search_types_outer: dict[str, filters.Filter] = {
            "icrs": filters.ICRSCoordinatesInRadiusFilter(outer_radius_degrees)
        }

        search_params = {}
        for idx, (_, obj) in enumerate(batch_objects.iterrows()):
            object_id = f"obj_{batch_start + idx}"
            search_params[object_id] = params.ICRSSearchParams(ra=obj[ra_column], dec=obj[dec_column])

        # Query the database for outer radius
        batch_results_outer = layer2_repo.query_batch(
            catalogs=[model.RawCatalog.ICRS],
            search_types=search_types_outer,
            search_params=search_params,
            limit=1000,
            offset=0,
        )

        # Process results for this batch
        for idx, (_, obj) in enumerate(batch_objects.iterrows()):
            object_id = f"obj_{batch_start + idx}"
            outer_matches = batch_results_outer.get(object_id, [])

            if len(outer_matches) == 0:
                # No objects in outer radius
                results[object_id] = CrossIdentificationResult(status="new")
            else:
                # Calculate distances to determine inner vs outer matches
                ra = obj[ra_column]
                dec = obj[dec_column]

                inner_matches = []
                outer_only_matches = []

                for match in outer_matches:
                    # Calculate angular distance
                    import math

                    # Find the ICRS data in the match
                    icrs_data = None
                    for catalog_obj in match.data:
                        if catalog_obj.catalog() == model.RawCatalog.ICRS:
                            icrs_data = catalog_obj
                            break

                    if icrs_data is None:
                        # Skip this match if no ICRS data found
                        continue

                    ra_diff = abs(icrs_data.ra - ra)  # type: ignore
                    dec_diff = abs(icrs_data.dec - dec)  # type: ignore

                    # Simple angular distance calculation (good enough for small angles)
                    distance_degrees = math.sqrt(ra_diff**2 + dec_diff**2)

                    if distance_degrees <= inner_radius_degrees:
                        inner_matches.append(match)
                    else:
                        outer_only_matches.append(match)

                # Apply the two-radius algorithm
                if len(inner_matches) == 1 and len(outer_only_matches) == 0:
                    # Exactly one object in inner radius, none between inner and outer
                    results[object_id] = CrossIdentificationResult(
                        status="existing", pgc_numbers=[inner_matches[0].pgc]
                    )
                else:
                    # Collision: multiple objects in inner radius, or objects between radii
                    all_pgc_numbers = [match.pgc for match in outer_matches]
                    results[object_id] = CrossIdentificationResult(status="collision", pgc_numbers=all_pgc_numbers)

    return results
