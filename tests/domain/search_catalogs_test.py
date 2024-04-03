import dataclasses
import unittest
from dataclasses import dataclass
from unittest import mock

from astroquery import vizier

from app.domain import model
from app.domain.usecases import Actions


@dataclass
class FieldStub:
    ID: str  # pylint: disable=invalid-name
    description: str
    unit: str


@dataclass
class TableStub:
    ID: str  # pylint: disable=invalid-name
    nrows: int
    fields: list


@dataclass
class CatalogStub:
    tables: list
    description: str


class SearchCatalogsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.actions = Actions(None, None)

    def test_run_without_metadata_no_tables(self):
        catalogs = {"V/II/table11": CatalogStub([], "test")}

        vizier.Vizier.find_catalogs = mock.MagicMock(return_value=catalogs)
        vizier.Vizier.get_catalog_metadata = mock.MagicMock(side_effect=IndexError("test"))

        actual = self.actions.search_catalogs(
            model.SearchCatalogsRequest(
                query="test query",
                page_size=10,
            )
        )
        expected = {
            "catalogs": [
                {
                    "id": "V/II/table11",
                    "description": "test",
                    "bibcode": "",
                    "url": "",
                    "tables": [],
                }
            ]
        }

        self.assertDictEqual(dataclasses.asdict(actual), expected)

    def test_run_with_metadata_no_tables(self):
        catalogs = {"V/II/table11": CatalogStub([], "test")}
        metadata = {"webpage": ["http://example.com"]}

        vizier.Vizier.find_catalogs = mock.MagicMock(return_value=catalogs)
        vizier.Vizier.get_catalog_metadata = mock.MagicMock(return_value=metadata)

        actual = self.actions.search_catalogs(
            model.SearchCatalogsRequest(
                query="test query",
                page_size=10,
            )
        )
        expected = {
            "catalogs": [
                {
                    "id": "V/II/table11",
                    "description": "test",
                    "bibcode": "",
                    "url": "http://example.com",
                    "tables": [],
                }
            ]
        }

        self.assertDictEqual(dataclasses.asdict(actual), expected)

    def test_run_without_metadata_one_table(self):
        catalog = CatalogStub(
            [TableStub("test_tbl", 101, [FieldStub("test_field", "test", "Myr")])],
            "test",
        )
        catalogs = {"V/II/table11": catalog}
        metadata = {"webpage": ["http://example.com"]}

        vizier.Vizier.find_catalogs = mock.MagicMock(return_value=catalogs)
        vizier.Vizier.get_catalog_metadata = mock.MagicMock(return_value=metadata)

        actual = self.actions.search_catalogs(
            model.SearchCatalogsRequest(
                query="test query",
                page_size=10,
            )
        )
        expected = {
            "catalogs": [
                {
                    "id": "V/II/table11",
                    "description": "test",
                    "bibcode": "",
                    "url": "http://example.com",
                    "tables": [
                        {
                            "id": "test_tbl",
                            "num_rows": 101,
                            "fields": [{"id": "test_field", "description": "test", "unit": "Myr"}],
                        }
                    ],
                }
            ]
        }

        self.assertDictEqual(dataclasses.asdict(actual), expected)
