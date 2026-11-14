from collections.abc import Mapping

from app.tasks.formula.constants import NAMED_CONSTANTS
from app.tasks.formula.functions import COL_FUNCTION, FUNCTIONS
from app.tasks.formula.operators import OPERATORS
from app.tasks.formula.values import Value


def build_namespace(columns: Mapping[str, Value]) -> dict[str, object]:
    return {
        "__builtins__": {},
        COL_FUNCTION.name: lambda name: columns[name],
        **{constant.name: constant.value for constant in NAMED_CONSTANTS},
        **{fn.name: fn.impl for fn in FUNCTIONS if fn.impl is not None},
    }


def expression_syntax_help() -> str:
    constants = ", ".join(f"`{constant.name}` ({constant.detail})" for constant in NAMED_CONSTANTS)
    functions = ", ".join(f"`{fn.signature}` ({fn.detail})" for fn in (COL_FUNCTION, *FUNCTIONS))
    operators = ", ".join(f"`{op.name}` ({op.detail})" for op in OPERATORS)
    return f"""\
## Expression syntax

Expressions are unit-aware and units are taken from column metadata.

Mathematical operations:
- Operators: {operators}
- Functions: {functions}
- Numbers are dimensionless
- String literals are supported
- Log columns (`mag`/`dex`) yield the bare exponent; multiply by the scale yourself

Available constants: {constants}.

## Examples

- Fill a column with a constant:
    - `1.5`
    - `180 * deg`
    - `"G"` - fills the column with a text "G"
- Copy another column: `col("ra")`
- Mathematical expression: `3 * 10 ** col("logd25") * arcsec`
- Conditional: `where(col("v") > 0, col("v"), 0)`
- Multi-way switch with a default: `select(col("t") == "E", 1, col("t") == "S", 2, 0)`
- Boolean logic: `and_(col("v") > 0, not_(isin(col("t"), "E", "S0")))`
- Text matching: `where(contains(col("name"), "NGC"), 1, 0)`
- Text slicing and concatenation: `"NGC " + slice(col("name"), 3, 7)`
- Parse text to a number: `num(slice(col("id"), 1, 5)) * deg`"""
