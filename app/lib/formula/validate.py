import ast
from dataclasses import asdict, dataclass
from typing import Annotated, final

import pydantic
from pydantic_core import PydanticCustomError

from app.lib.formula.constants import NAMED_CONSTANTS
from app.lib.formula.functions import COL_FUNCTION, FUNCTIONS


@final
@dataclass(frozen=True)
class ExpressionDiagnostic:
    message: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int


def _validate_expression_str(source: str) -> str:
    diagnostics = validate_expression(source)
    if not diagnostics:
        return source
    raise PydanticCustomError(
        "expression",
        "invalid expression",
        {"diagnostics": [asdict(item) for item in diagnostics]},
    )


ExpressionStr = Annotated[str, pydantic.AfterValidator(_validate_expression_str)]


def _from_syntax_error(error: SyntaxError, source: str) -> ExpressionDiagnostic:
    start_line = error.lineno if error.lineno and error.lineno > 0 else 1
    start_column = error.offset if error.offset and error.offset > 0 else 1
    end_line = error.end_lineno if error.end_lineno and error.end_lineno > 0 else start_line
    end_column = error.end_offset if error.end_offset and error.end_offset > start_column else start_column + 1
    lines = source.splitlines() or [source]
    if start_line == end_line and start_line <= len(lines):
        end_column = min(max(end_column, start_column + 1), len(lines[start_line - 1]) + 1)
    return ExpressionDiagnostic(
        message=error.msg or "invalid syntax",
        start_line=start_line,
        start_column=start_column,
        end_line=end_line,
        end_column=end_column,
    )


def _from_node(node: ast.AST, message: str) -> ExpressionDiagnostic:
    start_line = getattr(node, "lineno", 1) or 1
    start_column = (getattr(node, "col_offset", 0) or 0) + 1
    end_line = getattr(node, "end_lineno", None) or start_line
    end_offset = getattr(node, "end_col_offset", None)
    end_column = end_offset + 1 if end_offset is not None else start_column + 1
    if end_line == start_line and end_column <= start_column:
        end_column = start_column + 1
    return ExpressionDiagnostic(
        message=message,
        start_line=start_line,
        start_column=start_column,
        end_line=end_line,
        end_column=end_column,
    )


def _column_from_call(node: ast.Call) -> str | None:
    if not isinstance(node.func, ast.Name) or node.func.id != COL_FUNCTION.name:
        return None
    if node.keywords or len(node.args) != 1:
        raise ValueError(f"{COL_FUNCTION.name}() takes exactly one string argument")
    arg = node.args[0]
    if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
        raise ValueError(f"{COL_FUNCTION.name}() argument must be a string literal")
    return arg.value


def _is_known_name(name: str) -> bool:
    return any(constant.name == name for constant in NAMED_CONSTANTS) or any(fn.name == name for fn in FUNCTIONS)


def _collect_diagnostics(node: ast.AST, columns: set[str], diagnostics: list[ExpressionDiagnostic]) -> None:
    if isinstance(node, ast.Call):
        _collect_call_diagnostics(node, columns, diagnostics)
        return
    if isinstance(node, ast.Name):
        if not _is_known_name(node.id):
            message = (
                f"unknown name {node.id!r}; use {COL_FUNCTION.name}() for columns, "
                "a predefined constant/function, or quotes for a string literal"
            )
            diagnostics.append(_from_node(node, message))
        return
    for child in ast.iter_child_nodes(node):
        _collect_diagnostics(child, columns, diagnostics)


def _collect_call_diagnostics(node: ast.Call, columns: set[str], diagnostics: list[ExpressionDiagnostic]) -> None:
    try:
        column = _column_from_call(node)
    except ValueError as e:
        diagnostics.append(_from_node(node, str(e)))
        return
    if column is not None:
        columns.add(column)
        return
    if not isinstance(node.func, ast.Name):
        diagnostics.append(_from_node(node.func, "only simple function calls are allowed"))
        for child in ast.iter_child_nodes(node):
            _collect_diagnostics(child, columns, diagnostics)
        return
    if all(fn.name != node.func.id for fn in FUNCTIONS):
        diagnostics.append(_from_node(node.func, f"unknown function: {node.func.id}"))
    if node.keywords:
        diagnostics.append(_from_node(node, "keyword arguments are not allowed"))
    for arg in node.args:
        _collect_diagnostics(arg, columns, diagnostics)


def _parse_expression_ast(source: str) -> tuple[ast.AST | None, SyntaxError | None]:
    try:
        return ast.parse(source, mode="eval"), None
    except SyntaxError as first:
        if "\n" not in source:
            return None, first
        try:
            return ast.parse(f"({source})", mode="eval"), None
        except SyntaxError as wrapped:
            return None, wrapped


def diagnose_expression(source: str) -> tuple[ast.AST | None, frozenset[str], list[ExpressionDiagnostic]]:
    tree, syntax_error = _parse_expression_ast(source)
    if tree is None:
        message = (
            _from_syntax_error(syntax_error, source)
            if syntax_error is not None
            else ExpressionDiagnostic("invalid expression", 1, 1, 1, 2)
        )
        return None, frozenset(), [message]
    columns: set[str] = set()
    diagnostics: list[ExpressionDiagnostic] = []
    _collect_diagnostics(tree.body, columns, diagnostics)
    return tree, frozenset(columns), diagnostics


def validate_expression(source: str) -> list[ExpressionDiagnostic]:
    if not source.strip():
        return []
    _, _, diagnostics = diagnose_expression(source)
    return diagnostics
