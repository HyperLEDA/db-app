import enum
import re
from dataclasses import dataclass

# Use https://regex101.com/ to explain this regex
function_call_pattern = r'^([a-z0-9-]+):((?:[a-zA-Z0-9_+.]+)|(?:"[^"]+"))'
operator_pattern = r"^([a-z-]+)\s+"


class OperatorName(enum.Enum):
    AND = "and"
    OR = "or"


@dataclass
class OperatorToken:
    name: OperatorName


class FunctionName(enum.Enum):
    NAME = "name"
    POS = "pos"
    PGC = "pgc"


@dataclass
class FunctionToken:
    name: FunctionName
    value: str


@dataclass
class LParenToken:
    pass


@dataclass
class RParenToken:
    pass


Token = OperatorToken | FunctionToken | LParenToken | RParenToken


def parse_function_call(s: str) -> tuple[FunctionToken, int] | None:
    match = re.match(function_call_pattern, s)
    if match is None:
        return None

    groups = match.groups()
    if len(groups) != 2:
        raise RuntimeError(f"Unable to parse string: {s}")

    function_name_str, parameter = groups
    function_name = None

    chars_consumed = match.end()

    if function_name_str == "pos":
        function_name = FunctionName.POS
    elif function_name_str == "name":
        function_name = FunctionName.NAME
    elif function_name_str == "pgc":
        function_name = FunctionName.PGC
    else:
        raise RuntimeError(f"Unknown function: {function_name_str}")

    parameter = parameter.strip('"')

    return FunctionToken(function_name, parameter), chars_consumed


def parse_operator(s: str) -> tuple[OperatorToken, int] | None:
    match = re.match(operator_pattern, s)
    if match is None:
        return None

    operator_str = match.group(1)
    chars_consumed = match.end()

    if operator_str == "and":
        return OperatorToken(OperatorName.AND), chars_consumed

    if operator_str == "or":
        return OperatorToken(OperatorName.OR), 2

    raise RuntimeError(f"Unknown operator: {operator_str}")


def tokenize(s: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0

    while i < len(s):
        if s[i].isspace():
            i += 1
            continue

        if s[i] == "(":
            tokens.append(LParenToken())
            i += 1
            continue

        if s[i] == ")":
            tokens.append(RParenToken())
            i += 1
            continue

        parsed_operator = parse_operator(s[i:])
        if parsed_operator is not None:
            token, offset = parsed_operator
            tokens.append(token)
            i += offset
            continue

        parsed_func = parse_function_call(s[i:])
        if parsed_func is not None:
            token, offset = parsed_func
            tokens.append(token)
            i += offset
            continue

        raise RuntimeError(f"Invalid syntax at position {i}: {s[i:]}")

    return tokens
