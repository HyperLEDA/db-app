from dataclasses import dataclass

from app.domain.expressions import tokenizer


@dataclass
class AndNode:
    left: "Node"
    right: "Node"


@dataclass
class OrNode:
    left: "Node"
    right: "Node"


@dataclass
class FunctionNode:
    function: tokenizer.FunctionName
    value: str


Node = AndNode | OrNode | FunctionNode

PRECEDENCE = {
    tokenizer.OperatorName.AND: 1,
    tokenizer.OperatorName.OR: 0,
}


def peek[T](stack: list[T]) -> T | None:
    if stack:
        return stack[-1]

    return None


def infix_to_postfix(tokens: list[tokenizer.Token]) -> list[tokenizer.Token]:
    holding_stack: list[tokenizer.Token] = []
    output: list[tokenizer.Token] = []

    for token in tokens:
        if isinstance(token, tokenizer.FunctionToken):
            output.append(token)
        elif isinstance(token, tokenizer.OperatorToken):
            last_item = peek(holding_stack)
            while (
                last_item is not None
                and isinstance(last_item, tokenizer.OperatorToken)
                and PRECEDENCE[last_item.name] >= PRECEDENCE[token.name]
            ):
                output.append(holding_stack.pop())
                last_item = peek(holding_stack)

            holding_stack.append(token)
        elif isinstance(token, tokenizer.LParenToken):
            holding_stack.append(token)
        else:  # Right paren
            last_item = peek(holding_stack)
            while last_item is not None and not isinstance(last_item, tokenizer.LParenToken):
                output.append(holding_stack.pop())
                last_item = peek(holding_stack)

            if isinstance(last_item, tokenizer.LParenToken):
                holding_stack.pop()
            else:
                raise RuntimeError("Mismatched parentheses")

    while len(holding_stack) > 0:
        last_item = holding_stack.pop()
        if isinstance(last_item, tokenizer.LParenToken):
            raise RuntimeError("Mismatched parentheses")
        output.append(last_item)

    return output


def solve_postfix(tokens: list[tokenizer.Token]) -> Node:
    stack: list[Node] = []

    for token in tokens:
        if isinstance(token, tokenizer.FunctionToken):
            stack.append(FunctionNode(token.name, token.value))
        elif isinstance(token, tokenizer.OperatorToken):
            right = stack.pop()
            left = stack.pop()

            if token.name == tokenizer.OperatorName.AND:
                stack.append(AndNode(left, right))
            elif token.name == tokenizer.OperatorName.OR:
                stack.append(OrNode(left, right))

    return stack[0]


def parse_expression(s: str) -> Node:
    tokens = tokenizer.tokenize(s)
    postfix_tokens = infix_to_postfix(tokens)
    return solve_postfix(postfix_tokens)
