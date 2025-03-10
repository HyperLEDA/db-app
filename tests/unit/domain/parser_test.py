import unittest

from parameterized import param, parameterized

from app.domain.dataapi import parser, tokenizer


class InfixToPostfixTest(unittest.TestCase):
    @parameterized.expand(
        [
            param(
                "no operators",
                [
                    tokenizer.LParenToken(),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M33"),
                    tokenizer.RParenToken(),
                ],
                [tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M33")],
            ),
            param(
                "single operator",
                [
                    tokenizer.LParenToken(),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M33"),
                    tokenizer.OperatorToken(tokenizer.OperatorName.AND),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M34"),
                    tokenizer.RParenToken(),
                ],
                [
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M33"),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M34"),
                    tokenizer.OperatorToken(tokenizer.OperatorName.AND),
                ],
            ),
            param(
                "multiple operators",
                [
                    tokenizer.LParenToken(),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M33"),
                    tokenizer.OperatorToken(tokenizer.OperatorName.AND),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M34"),
                    tokenizer.OperatorToken(tokenizer.OperatorName.OR),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M35"),
                    tokenizer.RParenToken(),
                ],
                [
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M33"),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M34"),
                    tokenizer.OperatorToken(tokenizer.OperatorName.AND),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M35"),
                    tokenizer.OperatorToken(tokenizer.OperatorName.OR),
                ],
            ),
            param(
                "nested operators",
                [
                    tokenizer.LParenToken(),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M33"),
                    tokenizer.OperatorToken(tokenizer.OperatorName.AND),
                    tokenizer.LParenToken(),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M34"),
                    tokenizer.OperatorToken(tokenizer.OperatorName.OR),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M35"),
                    tokenizer.RParenToken(),
                    tokenizer.RParenToken(),
                ],
                [
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M33"),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M34"),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M35"),
                    tokenizer.OperatorToken(tokenizer.OperatorName.OR),
                    tokenizer.OperatorToken(tokenizer.OperatorName.AND),
                ],
            ),
        ]
    )
    def test_happy(self, name, input_tokens, expected):
        actual = parser.infix_to_postfix(input_tokens)
        self.assertEqual(actual, expected)

    @parameterized.expand(
        [
            param(
                "mismatched paren",
                [tokenizer.LParenToken(), tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M33")],
                "Mismatched parentheses",
            ),
        ]
    )
    def test_fails(self, name, input_tokens, expected_err):
        with self.assertRaises(RuntimeError) as err:
            _ = parser.infix_to_postfix(input_tokens)

        self.assertIn(expected_err, str(err.exception))


class SolvePostfixTest(unittest.TestCase):
    @parameterized.expand(
        [
            param(
                "single function",
                [tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M33")],
                parser.FunctionNode(tokenizer.FunctionName.NAME, "M33"),
            ),
            param(
                "single operator",
                [
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M33"),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M34"),
                    tokenizer.OperatorToken(tokenizer.OperatorName.AND),
                ],
                parser.AndNode(
                    left=parser.FunctionNode(tokenizer.FunctionName.NAME, "M33"),
                    right=parser.FunctionNode(tokenizer.FunctionName.NAME, "M34"),
                ),
            ),
            param(
                "multiple operators",
                [
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M33"),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M34"),
                    tokenizer.OperatorToken(tokenizer.OperatorName.AND),
                    tokenizer.FunctionToken(tokenizer.FunctionName.NAME, "M35"),
                    tokenizer.OperatorToken(tokenizer.OperatorName.OR),
                ],
                parser.OrNode(
                    left=parser.AndNode(
                        left=parser.FunctionNode(tokenizer.FunctionName.NAME, "M33"),
                        right=parser.FunctionNode(tokenizer.FunctionName.NAME, "M34"),
                    ),
                    right=parser.FunctionNode(tokenizer.FunctionName.NAME, "M35"),
                ),
            ),
        ]
    )
    def test_happy(self, name, input_tokens, expected):
        actual = parser.solve_postfix(input_tokens)
        self.assertEqual(actual, expected)
