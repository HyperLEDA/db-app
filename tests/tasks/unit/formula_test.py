import pydantic
import pytest
from astropy import units as u

from app.tasks import formula


def test_parse_records_column_references() -> None:
    expression = formula.parse('col("ra") + 1 * arcmin')
    assert expression.referenced_columns == frozenset({"ra"})


def test_parse_rejects_unknown_names() -> None:
    with pytest.raises(formula.ExpressionSyntaxError, match="unknown name"):
        formula.parse("not_a_column + 1")


def test_validate_blank_expression_is_allowed() -> None:
    assert formula.validate_expression("   ") == []


def test_expression_str_rejects_invalid_syntax() -> None:
    class Model(pydantic.BaseModel):
        source: formula.ExpressionStr

    with pytest.raises(pydantic.ValidationError):
        Model(source="col(")


def test_named_constant_converts_units() -> None:
    result = formula.evaluate(formula.parse("2 * deg"), {})
    assert isinstance(result, u.Quantity)
    assert result.to(u.Unit("arcmin")).value == pytest.approx(120)


def test_column_quantity_converts_with_expression() -> None:
    result = formula.evaluate(
        formula.parse('col("ra")'),
        {"ra": formula.column_quantity(60.0, "arcmin")},
    )
    assert isinstance(result, u.Quantity)
    assert result.to(u.Unit("deg")).value == pytest.approx(1)


def test_logarithmic_column_is_dimensionless() -> None:
    value = formula.column_quantity(12.5, "mag")
    assert isinstance(value, u.Quantity)
    assert value.unit == u.Unit("")
    assert value.value == pytest.approx(12.5)


def test_trig_and_where() -> None:
    sine = formula.evaluate(formula.parse("sin(90 * deg)"), {})
    assert isinstance(sine, u.Quantity)
    assert sine.to(u.Unit("")).value == pytest.approx(1)
    chosen = formula.evaluate(
        formula.parse('where(col("v") > 0, col("v"), 0)'),
        {"v": formula.column_quantity(3.0, "")},
    )
    assert isinstance(chosen, u.Quantity)
    assert chosen.value == pytest.approx(3)


def test_text_literal_and_value_to_str() -> None:
    assert formula.evaluate(formula.parse('"NGC 1"'), {}) == "NGC 1"
    assert formula.value_to_str(formula.evaluate(formula.parse("str(2 * deg)"), {})) == "2"


def test_syntax_help_lists_constants_and_functions() -> None:
    help_text = formula.expression_syntax_help()
    assert "`deg`" in help_text
    assert '`col("name")`' in help_text
    assert "`where(cond, then, else)`" in help_text
