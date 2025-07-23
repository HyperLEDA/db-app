from dataclasses import dataclass
from typing import Literal

import pandas

CrossIdentificationStatus = Literal["new", "existing", "collision"]


@dataclass
class CrossIdentificationResult:
    status: CrossIdentificationStatus
    pgc_numbers: list[int] | None = None


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
