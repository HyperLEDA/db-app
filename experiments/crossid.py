import os
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import from app
sys.path.insert(0, str(Path(__file__).parent / ".."))

from dataclasses import dataclass
from typing import Literal

import pandas
import structlog
from astropy import table
from astropy.io import fits

from app.data import model
from app.data.repositories import Layer2Repository
from app.data.repositories.layer2 import filters, params
from app.lib.storage import postgres

logger = structlog.get_logger()


def get_objects(fits_file_path: str) -> pandas.DataFrame:
    with fits.open(fits_file_path) as hdul:
        table_data = hdul[1].data  # type: ignore

        tbl = table.Table(table_data)
        df = tbl.to_pandas()

        print(f"Successfully loaded {len(df)} rows with {len(df.columns)} columns")
        print(f"Column names: {list(df.columns)}")

        return df


CrossIdentificationStatus = Literal["new", "existing", "collision"]


@dataclass
class CrossIdentificationResult:
    status: CrossIdentificationStatus
    pgc_numbers: list[int] | None = None


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

    logger.info(f"Using columns: {ra_column} for RA, {dec_column} for Dec")

    # Process objects in batches to avoid overwhelming the database
    batch_size = 1000
    total_objects = len(fast_objects)

    for batch_start in range(0, total_objects, batch_size):
        batch_end = min(batch_start + batch_size, total_objects)
        batch_objects = fast_objects.iloc[batch_start:batch_end]

        logger.info(f"Processing batch {batch_start // batch_size + 1}, objects {batch_start + 1}-{batch_end}")

        # Prepare batch query parameters
        search_types: dict[str, filters.Filter] = {"icrs": filters.ICRSCoordinatesInRadiusFilter(search_radius_degrees)}

        search_params = {}
        for idx, (_, obj) in enumerate(batch_objects.iterrows()):
            object_id = f"obj_{batch_start + idx}"
            search_params[object_id] = params.ICRSSearchParams(ra=obj[ra_column], dec=obj[dec_column])

        # Query the database
        batch_results = layer2_repo.query_batch(
            catalogs=[model.RawCatalog.ICRS],
            search_types=search_types,
            search_params=search_params,
            limit=1000,  # High limit to get all matches
            offset=0,
        )

        # Process results for this batch
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


def print_cross_identification_summary(results: dict[str, CrossIdentificationResult]) -> None:
    """Print a summary of cross-identification results."""
    total_objects = len(results)
    new_count = sum(1 for r in results.values() if r.status == "new")
    existing_count = sum(1 for r in results.values() if r.status == "existing")
    collision_count = sum(1 for r in results.values() if r.status == "collision")

    print("\nCross-Identification Summary:")
    print(f"Total objects: {total_objects}")
    print(f"New objects: {new_count} ({new_count / total_objects * 100:.1f}%)")
    print(f"Existing objects: {existing_count} ({existing_count / total_objects * 100:.1f}%)")
    print(f"Collisions: {collision_count} ({collision_count / total_objects * 100:.1f}%)")

    # Show some examples of collisions
    collision_examples = [(obj_id, result) for obj_id, result in results.items() if result.status == "collision"][:5]
    if collision_examples:
        print("\nExample collisions (showing first 5):")
        for obj_id, result in collision_examples:
            print(f"  {obj_id}: PGC numbers {result.pgc_numbers}")


def save_cross_identification_results(
    results: dict[str, CrossIdentificationResult], output_file: str = "cross_identification_results.csv"
) -> None:
    """Save cross-identification results to a CSV file."""
    import csv

    with open(output_file, "w", newline="") as csvfile:
        fieldnames = ["object_id", "status", "pgc_numbers"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for obj_id, result in results.items():
            pgc_str = ",".join(map(str, result.pgc_numbers)) if result.pgc_numbers else ""
            writer.writerow({"object_id": obj_id, "status": result.status, "pgc_numbers": pgc_str})

    print(f"Results saved to {output_file}")


def analyze_fast_objects_data(fast_objects: pandas.DataFrame) -> None:
    """Analyze the structure and content of the fast_objects data."""
    print("\nData Analysis:")
    print(f"Total objects: {len(fast_objects)}")
    print(f"Columns: {list(fast_objects.columns)}")

    # Check for coordinate columns
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

    if ra_column and dec_column:
        print(f"Coordinate columns found: {ra_column}, {dec_column}")

        # Show coordinate ranges
        ra_min, ra_max = fast_objects[ra_column].min(), fast_objects[ra_column].max()
        dec_min, dec_max = fast_objects[dec_column].min(), fast_objects[dec_column].max()

        print(f"RA range: {ra_min:.3f} to {ra_max:.3f} degrees")
        print(f"Dec range: {dec_min:.3f} to {dec_max:.3f} degrees")

        # Check for any obvious data quality issues
        ra_nan = fast_objects[ra_column].isna().sum()
        dec_nan = fast_objects[dec_column].isna().sum()

        if ra_nan > 0 or dec_nan > 0:
            print(f"Warning: {ra_nan} RA values and {dec_nan} Dec values are NaN")

    # Show first few rows
    print("\nFirst 5 objects:")
    print(fast_objects.head())


def main():
    search_radius_arcsec = 5
    search_radius_degrees = search_radius_arcsec / 3600.0

    print(f"Starting cross-identification with search radius: {search_radius_degrees} degrees")

    fast_objects = get_objects("experiments/data/fast.fits")

    # Analyze the data first
    analyze_fast_objects_data(fast_objects)

    # Database configuration - uncomment and modify as needed
    storage_config = postgres.PgStorageConfig(
        endpoint="dm2.sao.ru", port=5432, dbname="hyperleda", user="hyperleda", password=os.getenv("DB_PASS") or ""
    )

    storage = postgres.PgStorage(storage_config, logger)
    storage.connect()

    layer2_repo = Layer2Repository(storage, logger)

    try:
        results = cross_identify_objects(fast_objects, layer2_repo, search_radius_degrees)

        print_cross_identification_summary(results)

        for i, (obj_id, result) in enumerate(list(results.items())[:10]):
            print(f"{obj_id}: {result.status}")
            if result.pgc_numbers:
                print(f"  PGC numbers: {result.pgc_numbers}")

    except Exception as e:
        logger.error(f"Error during cross-identification: {e}")
        raise
    finally:
        storage.disconnect()


if __name__ == "__main__":
    main()
