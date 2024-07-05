import unittest

from app.domain.usecases.generalize_name_use_case import GeneralizeNameUseCase


class GeneralizeNameTest(unittest.TestCase):
    def setUp(self):
        self.use_case = GeneralizeNameUseCase()

    def test_andromeda(self):
        inp = [
            "And XXVIII",
            "Andromeda XXVIII",
            "And28",
            "ANDXXVIII",
            "andxxviii",
            "andromeda28"
        ]

        expected = "Andromeda 28"

        for source in inp:
            generalized = self.use_case.invoke(source)
            self.assertEqual(expected, generalized)

    def test_holmberg(self):
        inp = [
            "Holmberg II",
            "Holm II",
            "HoII",
            "Ho2",
            "Holmberg 2",
            "Holm2",
        ]

        expected = "Holmberg 2"

        for source in inp:
            generalized = self.use_case.invoke(source)
            self.assertEqual(expected, generalized)

    def test_zw(self):
        inp = [
            "7ZW223",
            "VII Zw 223",
            "ZW VII 223",
        ]

        expected = "7ZW 223"

        for source in inp:
            generalized = self.use_case.invoke(source)
            self.assertEqual(expected, generalized)

    def test_ngc(self):
        inp = [
            "NGC0017",
            "N17",
            "ngc17",
            "n017",
        ]

        expected = "NGC 17"

        for source in inp:
            generalized = self.use_case.invoke(source)
            self.assertEqual(expected, generalized)

    def test_ugc(self):
        inp = [
            "UGC 1493 A",
            "u1493a",
            "ugc1439a",
            "u1493A",
        ]

        expected = "UGC 1493A"

        for source in inp:
            generalized = self.use_case.invoke(source)
            self.assertEqual(expected, generalized)

    def test_ugca(self):
        inp = [
            "UGCA 035",
            "ua35",
            "UA035",
            "UGCA35",
        ]

        expected = "UGCA 35"

        for source in inp:
            generalized = self.use_case.invoke(source)
            self.assertEqual(expected, generalized)

    def test_pgc(self):
        inp = [
            "LEDA9843",
            "PGC 9843",
            "p009843",
            "leda 009843",
            "PGC009843",
        ]

        expected = "PGC 9843"

        for source in inp:
            generalized = self.use_case.invoke(source)
            self.assertEqual(expected, generalized)

    def test_eso(self):
        inp = [
            "ESO413-003",
            "eso 413-3",
            "ESO 413-03",
            "ESO 413- G 003",
        ]

        expected = "ESO 413-3"

        for source in inp:
            generalized = self.use_case.invoke(source)
            self.assertEqual(expected, generalized)

    def test_esolv(self):
        inp = [
            "ESO-LV 2530200",
            "ESO-LV 2530200",
            "ESO-LV 253-0200",
        ]

        expected = "ESO-LV 2530200"

        for source in inp:
            generalized = self.use_case.invoke(source)
            self.assertEqual(expected, generalized)

    def test_df(self):
        inp = [
            "6dF J0544383-434609",
            "6dFJ0544383-434609",
        ]

        expected = "6dF J0544383-434609"

        for source in inp:
            generalized = self.use_case.invoke(source)
            self.assertEqual(expected, generalized)

    def test_virgo(self):
        inp = [
            "Virgo A",
            "Vir A",
        ]

        expected = "Virgo A"

        for source in inp:
            generalized = self.use_case.invoke(source)
            self.assertEqual(expected, generalized)

    def test_sdss(self):
        inp = [
            "SDSS J123049.41+122328.1",
            "sdssJ123049.41+122328.1",
        ]

        expected = "SDSS J123049.41+122328.1"

        for source in inp:
            generalized = self.use_case.invoke(source)
            self.assertEqual(expected, generalized)
