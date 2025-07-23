import os
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import from app
sys.path.insert(0, str(Path(__file__).parent / ".."))

import pandas
import structlog
from astropy import table
from astropy.io import fits

from app.data.repositories import Layer2Repository
from app.lib.storage import postgres
from experiments.bayes import cross_identify_objects_bayesian
from experiments.entities import print_cross_identification_summary

logger = structlog.get_logger()


def get_objects(fits_file_path: str) -> pandas.DataFrame:
    with fits.open(fits_file_path) as hdul:
        table_data = hdul[1].data  # type: ignore

        tbl = table.Table(table_data)
        df = tbl.to_pandas()

        print(f"Successfully loaded {len(df)} rows with {len(df.columns)} columns")
        print(f"Column names: {list(df.columns)}")

        return df


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


def to_deg(arsec: float) -> float:
    return arsec / 3600


def main():
    search_radius_degrees = to_deg(10)

    inner_radius_degrees = to_deg(2)
    outer_radius_degrees = to_deg(10)

    print(f"Starting cross-identification with search radius: {search_radius_degrees} degrees")

    fast_objects = get_objects("experiments/data/fast.fits")
    fast_objects = fast_objects.head(5000)

    analyze_fast_objects_data(fast_objects)

    storage_config = postgres.PgStorageConfig(
        endpoint="dm2.sao.ru", port=5432, dbname="hyperleda", user="hyperleda", password=os.getenv("DB_PASS") or ""
    )

    storage = postgres.PgStorage(storage_config, logger)
    storage.connect()

    layer2_repo = Layer2Repository(storage, logger)

    try:
        # print("Testing single-radius algorithm...")
        # results_single = cross_identify_objects(fast_objects, layer2_repo, search_radius_degrees)

        # print("\nTesting two-radius algorithm...")
        # results_two_radius = cross_identify_objects_two_radius(
        #     fast_objects, layer2_repo, inner_radius_degrees, outer_radius_degrees
        # )

        print("\nTesting Bayesian algorithm...")
        # Use Bayesian-specific parameters
        lower_posterior_probability = 0.1
        upper_posterior_probability = 0.9
        cutoff_radius_degrees = to_deg(100)

        results_bayesian = cross_identify_objects_bayesian(
            fast_objects,
            layer2_repo,
            lower_posterior_probability=lower_posterior_probability,
            upper_posterior_probability=upper_posterior_probability,
            cutoff_radius_degrees=cutoff_radius_degrees,
        )

        # print()
        # print("Single radius:")
        # print_cross_identification_summary(results_single)

        # print()
        # print("Two-radius:")
        # print_cross_identification_summary(results_two_radius)

        print()
        print("Bayesian:")
        print_cross_identification_summary(results_bayesian)

    except Exception as e:
        logger.error(f"Error during cross-identification: {e}")
        raise
    finally:
        storage.disconnect()


if __name__ == "__main__":
    main()
