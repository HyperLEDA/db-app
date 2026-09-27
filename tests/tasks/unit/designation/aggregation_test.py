from astropy import table

from app.tasks.designation import aggregation


def test_aggregate_designation() -> None:
    priority_masks = [r"HIGH \d+", r"LOW \d+"]
    tbl = table.QTable(
        {
            "pgc": [1, 1, 1, 2, 2, 2, 3, 3, 3],
            "design": [
                "LOW 1",
                "LOW 1",
                "HIGH 1",
                "HIGH 1",
                "HIGH 2",
                "HIGH 2",
                "OTHER 1",
                "OTHER 1",
                "OTHER 2",
            ],
        }
    )

    result = aggregation.aggregate_designation(tbl, priority_masks)

    assert list(result["design"]) == ["HIGH 1", "HIGH 2", "OTHER 1"]
