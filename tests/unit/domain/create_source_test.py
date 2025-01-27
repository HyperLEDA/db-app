import unittest

from app.domain.adminapi.sources import construct_code


class ConstructCodeTest(unittest.TestCase):
    def test_run(self):
        tests = [
            (["Hawking J."], 2021, "Title", "2021_Hawking_Title"),
            (["Newton I.", "Einstein A."], 1650, "Theory of gravitation", "1650_Newton_Theory_of_gravitation"),
            (["Galilei G.", "Kepler J."], 1600, "Long title of the book", "1600_Galilei_Long_title_of"),
        ]

        for authors, year, title, code in tests:
            with self.subTest(code):
                self.assertEqual(construct_code(authors, year, title), code)
