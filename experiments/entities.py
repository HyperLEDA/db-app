from dataclasses import dataclass
from typing import Literal

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
