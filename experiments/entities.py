from dataclasses import dataclass
from typing import Literal

import pandas
import structlog

from app.data import model, repositories
from app.lib.storage import postgres

CrossIdentificationStatus = Literal["new", "existing", "collision"]


@dataclass
class CrossIdentificationResult:
    status: CrossIdentificationStatus
    pgc_numbers: list[int] | None = None


@dataclass
class PGCObjectInfo:
    pgc: int
    ra: float
    dec: float
    pos_err: float
    name: str


def get_pgc_objects_info(
    pgc_numbers: list[int],
    storage: postgres.PgStorage,
) -> list[PGCObjectInfo]:
    """
    Retrieve coordinates and names for PGC objects from the HyperLEDA database.

    Args:
        pgc_numbers: List of PGC numbers to query
        storage_config: Database connection configuration

    Returns:
        List of PGCObjectInfo objects containing PGC, coordinates, and names
    """
    logger = structlog.get_logger()

    layer2_repo = repositories.Layer2Repository(storage, logger)

    # Query for ICRS coordinates and designations
    catalogs = [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION]

    # Query with a large limit to get all requested PGCs
    layer2_objects = layer2_repo.query_pgc(
        catalogs=catalogs,
        pgc_numbers=pgc_numbers,
        limit=len(pgc_numbers),
    )

    pgc_info_list = []
    for obj in layer2_objects:
        ra = None
        dec = None
        pos_err = None
        name = None

        for catalog_obj in obj.data:
            if isinstance(catalog_obj, model.ICRSCatalogObject):
                ra = catalog_obj.ra
                dec = catalog_obj.dec
                pos_err = catalog_obj.e_ra or 1 / 3600.0
            elif isinstance(catalog_obj, model.DesignationCatalogObject):
                name = catalog_obj.designation

        if ra is None or dec is None or name is None or pos_err is None:
            continue

        pgc_info_list.append(PGCObjectInfo(pgc=obj.pgc, ra=ra, dec=dec, name=name, pos_err=pos_err))

    return pgc_info_list


def print_pgc_objects_info(pgc_numbers: list[int], storage_config: postgres.PgStorageConfig) -> None:
    """
    Print coordinates and names for PGC objects.

    Args:
        pgc_numbers: List of PGC numbers to query
        storage_config: Database connection configuration
    """
    pgc_info_list = get_pgc_objects_info(pgc_numbers, storage_config)

    print(f"\nInformation for {len(pgc_info_list)} PGC objects:")
    print("-" * 80)

    for info in pgc_info_list:
        ra_str = f"{info.ra:.6f}" if info.ra is not None else "N/A"
        dec_str = f"{info.dec:.6f}" if info.dec is not None else "N/A"
        name_str = info.name if info.name else "N/A"

        print(f"PGC {info.pgc:>8}: RA={ra_str:>12}, Dec={dec_str:>12}, Name='{name_str}'")


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
    results: dict[str, CrossIdentificationResult],
    fast_objects: pandas.DataFrame,
    output_file: str = "cross_identification_results.csv",
) -> None:
    """Save cross-identification results to a CSV file with detailed information."""
    import csv

    # Find coordinate and name columns
    ra_column = None
    dec_column = None
    name_column = None

    for ra_name in ["ra", "RAJ2000", "RA", "ra_deg"]:
        if ra_name in fast_objects.columns:
            ra_column = ra_name
            break

    for dec_name in ["dec", "DEJ2000", "DEC", "dec_deg"]:
        if dec_name in fast_objects.columns:
            dec_column = dec_name
            break

    for name_name in ["Name", "name", "OBJECT", "object"]:
        if name_name in fast_objects.columns:
            name_column = name_name
            break

    if not ra_column or not dec_column:
        raise ValueError(f"Could not find RA/Dec columns. Available columns: {list(fast_objects.columns)}")

    with open(output_file, "w", newline="") as csvfile:
        fieldnames = ["object_id", "ra", "dec", "name", "status", "pgc_numbers"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for obj_id, result in results.items():
            # Extract batch index from object_id (format: "obj_<index>")
            batch_idx = int(obj_id.split("_")[1])
            obj = fast_objects.iloc[batch_idx]

            # Get coordinates
            ra = obj[ra_column]
            dec = obj[dec_column]

            # Get name (use empty string if not found)
            name = obj[name_column] if name_column else ""

            # Format PGC numbers
            pgc_str = ",".join(map(str, result.pgc_numbers)) if result.pgc_numbers else ""

            writer.writerow(
                {
                    "object_id": obj_id,
                    "ra": ra,
                    "dec": dec,
                    "name": name,
                    "status": result.status,
                    "pgc_numbers": pgc_str,
                }
            )

    print(f"Results saved to {output_file}")
    print(f"Columns: {fieldnames}")
    print(f"Total objects: {len(results)}")
