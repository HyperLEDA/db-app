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
    # dict pgc -> probability of match
    pgc_numbers: dict[int, float] | None = None


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


@dataclass
class CrossIDInfo:
    ra: float
    dec: float
    pos_err: float
    name: str
    status: CrossIdentificationStatus
    pgc_numbers: dict[int, float]


def save_cross_identification_results(
    results: dict[str, CrossIdentificationResult],
    fast_objects: pandas.DataFrame,
    output_file: str = "cross_identification_results.csv",
) -> None:
    output = pandas.DataFrame()

    output["ra"] = fast_objects["RAJ2000"]
    output["dec"] = fast_objects["DEJ2000"]
    output["pos_err"] = fast_objects["ePos"]
    output["name"] = fast_objects["Name"]

    statuses = [""] * len(results)
    pgc_numbers = [""] * len(results)

    for obj_id, result in results.items():
        batch_idx = int(obj_id.split("_")[1])

        statuses[batch_idx] = result.status
        pgc_numbers[batch_idx] = str(result.pgc_numbers) or ""

    output["status"] = statuses
    output["pgc_numbers"] = pgc_numbers
    output.to_csv(output_file, index=False)

    print(f"Results saved to {output_file}")
    print(f"Total objects: {len(output)}")
