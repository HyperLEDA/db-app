from collections.abc import Callable
from typing import Any

import pydantic
import pytest
from astropy import units as u

from app.tasks import formula


def test_parse_validation_and_helpers() -> None:
    assert formula.parse('col("ra") + 1 * arcmin').referenced_columns == frozenset({"ra"})
    with pytest.raises(formula.ExpressionSyntaxError, match="unknown name"):
        formula.parse("not_a_column + 1")
    assert formula.validate_expression("   ") == []

    class Model(pydantic.BaseModel):
        source: formula.ExpressionStr

    with pytest.raises(pydantic.ValidationError):
        Model(source="col(")

    value = formula.column_quantity(12.5, "mag")
    assert value.unit == u.Unit("") and value.value == pytest.approx(12.5)
    help_text = formula.expression_syntax_help()
    assert "`deg`" in help_text and '`col("name")`' in help_text and "`where(cond, then, else)`" in help_text


@pytest.mark.parametrize(
    ("source", "columns", "check"),
    [
        ("2 * deg", {}, lambda r: r.to(u.Unit("arcmin")).value == pytest.approx(120)),
        ('col("ra")', {"ra": ("arcmin", 60.0)}, lambda r: r.to(u.Unit("deg")).value == pytest.approx(1)),
        ("sin(90 * deg)", {}, lambda r: r.to(u.Unit("")).value == pytest.approx(1)),
        ('where(col("v") > 0, col("v"), 0)', {"v": ("", 3.0)}, lambda r: r.value == pytest.approx(3)),
        ('"NGC 1"', {}, lambda r: r == "NGC 1"),
        ("str(2 * deg)", {}, lambda r: formula.value_to_str(r) == "2"),
    ],
)
def test_evaluate_cases(source: str, columns: dict[str, tuple[str, float]], check: Callable[[Any], bool]) -> None:
    namespace = {name: formula.column_quantity(value, unit) for name, (unit, value) in columns.items()}
    assert check(formula.evaluate(formula.parse(source), namespace))
