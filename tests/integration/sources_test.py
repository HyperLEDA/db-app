import unittest

import structlog

from app.data import repository
from app.domain import model, usecases
from app.lib import testing

log = structlog.get_logger()


class SourcesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = testing.TestPostgresStorage("postgres/migrations")
        cls.storage.start()

        cls.repo = repository.DataRespository(cls.storage.get_storage())
        cls.actions = usecases.Actions(cls.repo)

    @classmethod
    def tearDownClass(cls):
        cls.storage.stop()

    def tearDown(self):
        self.storage.clear()

    def test_create_one_source_success(self):
        create_response = self.actions.create_source(
            model.CreateSourceRequest(
                "publication",
                {"bibcode": "1992ApJ…400L…1W", "author": "Test author et al.", "year": 2000, "title": "Test research"},
            ),
        )
        get_response = self.actions.get_source(model.GetSourceRequest(id=create_response.id))

        self.assertEqual(get_response.type, "publication")
        self.assertEqual(get_response.metadata["bibcode"], "1992ApJ…400L…1W")
        self.assertEqual(get_response.metadata["author"], ["Test author et al."])
        self.assertEqual(get_response.metadata["year"], 2000)
        self.assertEqual(get_response.metadata["title"], "Test research")

    def test_create_one_source_wrong_type(self):
        with self.assertRaises(Exception):
            _ = self.actions.create_source(
                model.CreateSourceRequest("some_non-exitent-type", {}),
            )

    def test_create_one_source_not_enough_metadata(self):
        with self.assertRaises(Exception):
            _ = self.actions.create_source(
                model.CreateSourceRequest(
                    "publication",
                    {"author": "Test author et al."},
                ),
            )

    def test_create_two_sources_duplicate(self):
        _ = self.actions.create_source(
            model.CreateSourceRequest(
                "publication",
                {"bibcode": "2000ApJ…400L…1W", "author": "Test author et al.", "year": 2000, "title": "Test research"},
            ),
        )

        with self.assertRaises(Exception):
            _ = self.actions.create_source(
                model.CreateSourceRequest(
                    "publication",
                    {
                        "bibcode": "2000ApJ…400L…1W",
                        "author": "Test author et al.",
                        "year": 2000,
                        "title": "Test research",
                    },
                ),
            )

    def test_get_non_existent_source_id(self):
        with self.assertRaises(Exception):
            _ = self.actions.get_source(model.GetSourceRequest(id=12321))

    def test_get_list_first_page_full(self):
        for i in range(25):
            _ = self.actions.create_source(
                model.CreateSourceRequest(
                    "publication",
                    {
                        "bibcode": f"20{i:02d}ApJ…401L…1W",
                        "author": "Test author et al.",
                        "year": 2000,
                        "title": "Test research",
                    },
                ),
            )

        result = self.actions.get_source_list(model.GetSourceListRequest("publication", 10, 0))

        self.assertEqual(len(result.sources), 10)

    def test_get_list_second_page_not_full(self):
        for i in range(15):
            _ = self.actions.create_source(
                model.CreateSourceRequest(
                    "publication",
                    {
                        "bibcode": f"20{i:02d}ApJ…402L…1W",
                        "author": "Test author et al.",
                        "year": 2000,
                        "title": "Test research",
                    },
                ),
            )

        result = self.actions.get_source_list(model.GetSourceListRequest("publication", 10, 1))

        self.assertEqual(len(result.sources), 5)

    def test_get_list_no_sources(self):
        result = self.actions.get_source_list(model.GetSourceListRequest("publication", 10, 0))

        self.assertEqual(len(result.sources), 0)
