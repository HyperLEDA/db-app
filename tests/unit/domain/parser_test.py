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
    def test_table(self, name, input_tokens, expected):
        actual = parser.infix_to_postfix(input_tokens)
        self.assertEqual(actual, expected)
