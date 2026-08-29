import unittest

from app import catalogs
from app.adminapi import model
from app.adminapi.domain import crossmatch


class CatalogsFromObjectTest(unittest.TestCase):
    def test_includes_nature_when_present(self) -> None:
        record = model.Record(
            id="rec1",
            data=[
                catalogs.DesignationCatalogObject(design="NGC 1"),
                catalogs.NatureCatalogObject(type_name="G"),
            ],
        )

        result = crossmatch.catalogs_from_object(record)

        self.assertIsNotNone(result.designation)
        assert result.designation is not None
        self.assertEqual(result.designation.name, "NGC 1")
        self.assertIsNotNone(result.nature)
        assert result.nature is not None
        self.assertEqual(result.nature.type_name, "G")

    def test_omits_nature_when_absent(self) -> None:
        record = model.Record(
            id="rec1",
            data=[catalogs.DesignationCatalogObject(design="NGC 1")],
        )

        result = crossmatch.catalogs_from_object(record)

        self.assertIsNone(result.nature)
