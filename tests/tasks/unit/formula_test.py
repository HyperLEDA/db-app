from collections.abc import Callable
from typing import Any

import pydantic
import pytest
from astropy import units as u

from app.lib import formula


def test_parse_validation_and_helpers() -> None:
    assert formula.parse('col("ra") + 1 * arcmin').referenced_columns == frozenset({"ra"})
    with pytest.raises(formula.ExpressionSyntaxError, match="quotes for a string literal"):
        formula.parse("not_a_column + 1")
    assert formula.validate_expression("   ") == []
    multiline = formula.parse('"SDSS J"\n+ zfill(str(floor(col("ra") / deg / 15)), 2)')
    assert multiline.referenced_columns == frozenset({"ra"})
    assert (
        formula.value_to_str(formula.evaluate(multiline, {"ra": formula.column_quantity(195.0, "deg")})) == "SDSS J13"
    )

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


def _run(source: str, columns: dict[str, tuple[str, Any]] | None = None) -> Any:
    namespace = {name: formula.column_quantity(value, unit) for name, (unit, value) in (columns or {}).items()}
    return formula.evaluate(formula.parse(source), namespace)


TEXT = {"t": ("", ["E", "S0", "Sb", "E"]), "name": ("", ["NGC 1", " ngc 22 ", "IC 5", "NGC 100"])}
TEXT_UNIT = {"t": ("hourangle", ["E", "S0", "Sb", "E"])}
NUMS = {"v": ("", [1.0, -2.0, 3.0, 0.0])}


@pytest.mark.parametrize(
    ("source", "columns", "expected"),
    [
        ('col("t") == "E"', TEXT, [True, False, False, True]),
        ('col("t") == "E"', TEXT_UNIT, [True, False, False, True]),
        ('col("t") != "E"', TEXT_UNIT, [False, True, True, False]),
        ('"E" == col("t")', TEXT_UNIT, [True, False, False, True]),
        ('and_(col("v") > 0, col("v") < 3)', NUMS, [True, False, False, False]),
        ('and_(col("v") > -5, col("v") < 3, col("v") != 0)', NUMS, [True, True, False, False]),
        ('or_(col("v") > 2, col("v") < 0)', NUMS, [False, True, True, False]),
        ('not_(col("v") > 0)', NUMS, [False, True, False, True]),
        ('isin(col("t"), "E", "Sb")', TEXT_UNIT, [True, False, True, True]),
        ('isin(col("v"), 1, 3)', NUMS, [True, False, True, False]),
        ('isin(col("v"), 1000 * unit("m") / unit("km"))', NUMS, [True, False, False, False]),
        ('contains(col("name"), "NGC")', TEXT, [True, False, False, True]),
        ('startswith(col("name"), "IC")', TEXT, [False, False, True, False]),
        ('endswith(col("name"), "1")', TEXT, [True, False, False, False]),
    ],
)
def test_boolean_results(source: str, columns: dict[str, tuple[str, Any]], expected: list[bool]) -> None:
    assert _run(source, columns).tolist() == expected


@pytest.mark.parametrize(
    ("source", "columns", "expected"),
    [
        ('upper(col("name"))', TEXT, ["NGC 1", " NGC 22 ", "IC 5", "NGC 100"]),
        ('lower(col("name"))', TEXT, ["ngc 1", " ngc 22 ", "ic 5", "ngc 100"]),
        ('strip(col("name"))', TEXT, ["NGC 1", "ngc 22", "IC 5", "NGC 100"]),
        ('replace(col("name"), "NGC", "N")', TEXT, ["N 1", " ngc 22 ", "IC 5", "N 100"]),
        ('slice(col("name"), 0, 3)', TEXT, ["NGC", " ng", "IC ", "NGC"]),
        ('slice(col("name"), 4, 10)', TEXT, ["1", " 22 ", "", "100"]),
        ('"X" + slice(col("name"), 0, 2) + col("t")', TEXT_UNIT | TEXT, ["XNGE", "X nS0", "XICSb", "XNGE"]),
        ('zfill(slice(col("name"), 4, 10), 4)', TEXT, ["0001", " 22 ", "0000", "0100"]),
    ],
)
def test_string_results(source: str, columns: dict[str, tuple[str, Any]], expected: list[str]) -> None:
    assert _run(source, columns).tolist() == expected


def test_string_scalars_and_numbers() -> None:
    assert _run('upper("ngc")') == "NGC"
    assert bool(_run('contains("NGC 1", "GC")'))
    length = _run('len(col("name"))', TEXT)
    assert length.unit == u.Unit("") and length.value.tolist() == [5, 8, 4, 7]
    assert _run('find(col("name"), "C")', TEXT).value.tolist() == [2, -1, 1, 2]
    parsed = _run('num(col("name"))', {"name": ("", ["1", "22", "3.5"])})
    assert parsed.unit == u.Unit("") and parsed.value.tolist() == [1.0, 22.0, 3.5]
    assert _run('num("2.5") * deg').to(u.Unit("deg")).value == pytest.approx(2.5)
    with pytest.raises(formula.ExpressionEvaluationError):
        _run('num(col("name"))', TEXT)


def test_select_numeric_text_and_units() -> None:
    result = _run('select(col("v") > 2, 10, col("v") < 0, 20, 0)', NUMS)
    assert result.unit == u.Unit("") and result.value.tolist() == [0, 20, 10, 0]

    labelled = _run('select(col("t") == "E", "elliptical", col("t") == "S0", "lenticular", "other")', TEXT)
    assert labelled.tolist() == ["elliptical", "lenticular", "other", "elliptical"]
    labelled_unit = _run('select(col("t") == "E", "elliptical", "other")', TEXT_UNIT)
    assert labelled_unit.tolist() == ["elliptical", "other", "other", "elliptical"]

    aligned = _run('select(col("v") > 2, 1 * deg, col("v") < 0, 60 * arcmin, 30 * arcmin)', NUMS)
    assert aligned.unit == u.Unit("deg")
    assert aligned.value.tolist() == pytest.approx([0.5, 1.0, 1.0, 0.5])

    with pytest.raises(formula.ExpressionEvaluationError):
        _run('select(col("v") > 0, 1)', NUMS)


def test_math_helpers_keep_units() -> None:
    columns = {"x": ("deg", [-1.26, 2.5, 3.14159])}
    assert _run('abs(col("x"))', columns).value.tolist() == pytest.approx([1.26, 2.5, 3.14159])
    assert _run('abs(col("x"))', columns).unit == u.Unit("deg")
    assert _run('floor(col("x"))', columns).value.tolist() == [-2, 2, 3]
    assert _run('ceil(col("x"))', columns).value.tolist() == [-1, 3, 4]
    rounded = _run('round(col("x"), 1)', columns)
    assert rounded.unit == u.Unit("deg") and rounded.value.tolist() == pytest.approx([-1.3, 2.5, 3.1])
    assert _run("abs(-3)").value == 3


def test_new_functions_in_help() -> None:
    help_text = formula.expression_syntax_help()
    for name in ("select", "isin", "contains", "and_", "or_", "not_", "slice", "zfill", "num", "round"):
        assert f"`{name}(" in help_text
