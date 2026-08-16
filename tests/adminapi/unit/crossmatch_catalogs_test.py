import unittest

from app.adminapi.domain import crossmatch
from app.data import model


class CatalogsFromObjectTest(unittest.TestCase):
    def test_includes_nature_when_present(self) -> None:
        record = model.Record(
            id="rec1",
            data=[
                model.DesignationCatalogObject(design="NGC 1"),
                model.NatureCatalogObject(type_name="G"),
            ],
        )

        catalogs = crossmatch.catalogs_from_object(record)

        self.assertIsNotNone(catalogs.designation)
        assert catalogs.designation is not None
        self.assertEqual(catalogs.designation.name, "NGC 1")
        self.assertIsNotNone(catalogs.nature)
        assert catalogs.nature is not None
        self.assertEqual(catalogs.nature.type_name, "G")

    def test_omits_nature_when_absent(self) -> None:
        record = model.Record(
            id="rec1",
            data=[model.DesignationCatalogObject(design="NGC 1")],
        )

        catalogs = crossmatch.catalogs_from_object(record)

        self.assertIsNone(catalogs.nature)
