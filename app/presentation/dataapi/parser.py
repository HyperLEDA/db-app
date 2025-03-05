import enum
import re
from dataclasses import dataclass

# Use https://regex101.com/ to explain this regex
function_call_pattern = r'([a-zA-Z0-9-]+):((?:[^:\s"]+)|(?:"[^"]+"))'


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


def parse_function_call(s: str) -> tuple[FunctionName, str] | None:
    match = re.match(function_call_pattern, s)
    if match is None:
        return None

    groups = match.groups()
    if len(groups) != 2:
        raise RuntimeError(f"Unable to parse string: {s}")

    function_name_str, parameter = groups
    function_name = None

    if function_name_str == "pos":
        function_name = FunctionName.POS
    elif function_name_str == "name":
        function_name = FunctionName.NAME
    elif function_name_str == "pgc":
        function_name = FunctionName.PGC
    else:
        raise RuntimeError(f"Unknown function: {function_name_str}")

    parameter = parameter.strip('"')

    return function_name, parameter


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

        if s[i:].startswith("and "):
            tokens.append(OperatorToken(OperatorName.AND))
            i += 1
            continue

        if s[i:].startswith("or "):
            tokens.append(OperatorToken(OperatorName.OR))
            i += 1
            continue

        parsed_func = parse_function_call(s[i:])
        if parsed_func is not None:
            func_name, params = parsed_func
            tokens.append(FunctionToken(func_name, params))
            continue

        raise RuntimeError(f"Invalid syntax at position {i}: {s[i:]}")

    return tokens
