import unittest

from parameterized import param, parameterized

from app.presentation.dataapi.parser import (
    FunctionName,
    FunctionToken,
    OperatorName,
    OperatorToken,
    parse_function_call,
    parse_operator,
)


class ParserTest(unittest.TestCase):
    @parameterized.expand(
        [
            param("name:M33", FunctionToken(FunctionName.NAME, "M33")),
            param("pos:J123049.32+122233.2", FunctionToken(FunctionName.POS, "J123049.32+122233.2")),
            param(
                "pos:\"12h 30m 49.32s +12d 23' 33.2''\"",
                FunctionToken(FunctionName.POS, "12h 30m 49.32s +12d 23' 33.2''"),
            ),
            param("pos:B122817.46+123907.1", FunctionToken(FunctionName.POS, "B122817.46+123907.1")),
            param("pos:G283.79325+74.47647", FunctionToken(FunctionName.POS, "G283.79325+74.47647")),
            param("pos:M33", FunctionToken(FunctionName.POS, "M33")),
            param("pgc:123456", FunctionToken(FunctionName.PGC, "123456")),
            param(
                "pos:\"12h 30m 49.32s +12d 23' 33.2''\" there is some additional text",
                FunctionToken(FunctionName.POS, "12h 30m 49.32s +12d 23' 33.2''"),
            ),
            param("pgc:123456 some text", FunctionToken(FunctionName.PGC, "123456")),
            param("totally not function", None),
            param("and (name:M33)", None),
        ],
    )
    def test_parse_function_call_happy(self, s, expected):
        actual = parse_function_call(s)

        if actual is None:
            self.assertEqual(actual, expected)
        else:
            actual_token, _ = actual
            self.assertEqual(actual_token, expected)

    @parameterized.expand(
        [
            param("nonexistingfunc:M33", "Unknown function"),
        ],
    )
    def test_parse_function_call_errors(self, s, err_substr):
        with self.assertRaises(RuntimeError) as err:
            _ = parse_function_call(s)

        self.assertIn(err_substr, str(err.exception))

    @parameterized.expand(
        [
            param("and ", OperatorToken(OperatorName.AND)),
            param("and name:M33 or name:M44", OperatorToken(OperatorName.AND)),
            param("or (((", OperatorToken(OperatorName.OR)),
            param("not:an:operator", None),
        ]
    )
    def test_parse_operator_happy(self, s, expected):
        actual = parse_operator(s)

        if actual is None:
            self.assertEqual(actual, expected)
        else:
            actual_token, _ = actual
            self.assertEqual(actual_token, expected)

    @parameterized.expand(
        [
            param("nonexistentoperator ", "Unknown operator"),
        ],
    )
    def test_parse_operator_errors(self, s, err_substr):
        with self.assertRaises(RuntimeError) as err:
            _ = parse_operator(s)

        self.assertIn(err_substr, str(err.exception))
