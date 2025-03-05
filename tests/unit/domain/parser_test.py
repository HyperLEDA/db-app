import unittest

from parameterized import param, parameterized

from app.presentation.dataapi.parser import FunctionName, parse_function_call


class ParserTests(unittest.TestCase):
    @parameterized.expand(
        [
            param("name:M33", (FunctionName.NAME, "M33")),
            param("pos:J123049.32+122233.2", (FunctionName.POS, "J123049.32+122233.2")),
            param("pos:\"12h 30m 49.32s +12d 23' 33.2''\"", (FunctionName.POS, "12h 30m 49.32s +12d 23' 33.2''")),
            param("pos:B122817.46+123907.1", (FunctionName.POS, "B122817.46+123907.1")),
            param("pos:G283.79325+74.47647", (FunctionName.POS, "G283.79325+74.47647")),
            param("pos:M33", (FunctionName.POS, "M33")),
            param("pgc:123456", (FunctionName.PGC, "123456")),
            param(
                "pos:\"12h 30m 49.32s +12d 23' 33.2''\" there is some additional text",
                (FunctionName.POS, "12h 30m 49.32s +12d 23' 33.2''"),
            ),
            param("pgc:123456 some text", (FunctionName.PGC, "123456")),
            param("totally not function", None),
            param("and (name:M33)", None),
        ],
    )
    def test_parse_function_call_happy(self, s, expected):
        actual = parse_function_call(s)

        self.assertEqual(actual, expected)

    @parameterized.expand(
        [
            param("nonexistingfunc:M33", "Unknown function"),
        ],
    )
    def test_parse_function_call_errors(self, s, err_substr):
        with self.assertRaises(RuntimeError) as err:
            _ = parse_function_call(s)

        self.assertIn(err_substr, str(err.exception))
