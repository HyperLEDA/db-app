import unittest

from pandas import DataFrame

from app.domain.model.layer0.names.comma_name_descr import CommaNameDescr
from app.domain.model.layer0.names.multi_col_name_descr import MultyColNameDescr
from app.domain.model.layer0.names.single_col_name_descr import SingleColNameDescr


class NamesParsingTest(unittest.TestCase):
    def test_multi_name_descr(self):
        data = DataFrame(
            {
                "name_1": ["a", "b", "c", "d"],
                "name_2": ["f", "g", "h", "j"],
                "col1": [1, 2, 3, 4],
            }
        )
        name_descr = MultyColNameDescr("name_1", ["name_1", "name_2"])

        res = name_descr.parse_name(data)

        self.assertEqual(res[0], ("a", ["a", "f"]))
        self.assertEqual(res[2], ("c", ["c", "h"]))

    def test_single_name_descr(self):
        data = DataFrame(
            {
                "name_1": ["a", "b", "c", "d"],
                "col1": [1, 2, 3, 4],
            }
        )
        name_descr = SingleColNameDescr("name_1")

        res = name_descr.parse_name(data)

        self.assertEqual(res[0], ("a", ["a"]))
        self.assertEqual(res[3], ("d", ["d"]))

    def test_comma_name_descr(self):
        data = DataFrame(
            {
                "name_1": ["a,s", "b,d", "c,f", "d,g"],
                "col1": [1, 2, 3, 4],
            }
        )
        name_descr = CommaNameDescr("name_1", 1)

        res = name_descr.parse_name(data)

        self.assertEqual(res[0], ("s", ["a", "s"]))
        self.assertEqual(res[2], ("f", ["c", "f"]))
