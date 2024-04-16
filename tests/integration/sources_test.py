import unittest

import structlog

from app.data import repositories
from app.domain import model, usecases
from app.lib import testing


class SourcesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = testing.get_or_create_test_postgres_storage()

        common_repo = repositories.CommonRepository(cls.storage.get_storage(), structlog.get_logger())
        layer0_repo = repositories.Layer0Repository(cls.storage.get_storage(), structlog.get_logger())
        layer1_repo = repositories.Layer1Repository(cls.storage.get_storage(), structlog.get_logger())
        cls.actions = usecases.Actions(common_repo, layer0_repo, layer1_repo, None, None, structlog.get_logger())

    def tearDown(self):
        self.storage.clear()

    def test_create_one_source_success(self):
        create_response = self.actions.create_source(
            model.CreateSourceRequest(
                bibcode="1992ApJ...400L...1W",
                authors=["Test author et al."],
                year=2000,
                title="Test research",
            ),
        )
        get_response = self.actions.get_source(model.GetSourceRequest(id=create_response.id))

        self.assertEqual(get_response.bibcode, "1992ApJ...400L...1W")
        self.assertEqual(get_response.authors, ["Test author et al."])
        self.assertEqual(get_response.year, 2000)
        self.assertEqual(get_response.title, "Test research")

    def test_create_two_sources_duplicate(self):
        _ = self.actions.create_source(
            model.CreateSourceRequest(
                bibcode="2000ApJ...400L...1W",
                authors=["Test author et al."],
                year=2000,
                title="Test research",
            ),
        )

        with self.assertRaises(Exception):
            _ = self.actions.create_source(
                model.CreateSourceRequest(
                    bibcode="2000ApJ...400L...1W",
                    authors=["Test author et al."],
                    year=2000,
                    title="Test research",
                ),
            )

    def test_get_non_existent_source_id(self):
        with self.assertRaises(Exception):
            _ = self.actions.get_source(model.GetSourceRequest(id=12321))

    def test_get_list_first_page_full(self):
        for i in range(25):
            _ = self.actions.create_source(
                model.CreateSourceRequest(
                    bibcode=f"20{i:02d}ApJ...401L...1W",
                    authors=["Test author et al."],
                    year=2000,
                    title=f"20{i:02d}ApJ...401L...1W",
                ),
            )

        result = self.actions.get_source_list(model.GetSourceListRequest("ApJ", 10, 0))

        self.assertEqual(len(result.sources), 10)

    def test_get_filtered_titles(self):
        _ = self.actions.create_source(
            model.CreateSourceRequest(
                bibcode="2001ApJ...401L...1W",
                authors=["Test author et al."],
                year=2000,
                title="Test research",
            ),
        )
        _ = self.actions.create_source(
            model.CreateSourceRequest(
                bibcode="2002ApJ...401L...1W",
                authors=["Test author et al."],
                year=2000,
                title="Test important research",
            ),
        )

        result = self.actions.get_source_list(model.GetSourceListRequest("Test", 10, 0))
        self.assertEqual(len(result.sources), 2)

        result = self.actions.get_source_list(model.GetSourceListRequest("important", 10, 0))
        self.assertEqual(len(result.sources), 1)

    def test_get_list_second_page_not_full(self):
        for i in range(15):
            _ = self.actions.create_source(
                model.CreateSourceRequest(
                    bibcode=f"20{i:02d}ApJ...402L...1W",
                    authors=["Test author et al."],
                    year=2000,
                    title=f"20{i:02d}ApJ...402L...1W",
                ),
            )

        result = self.actions.get_source_list(model.GetSourceListRequest("ApJ", 10, 1))

        self.assertEqual(len(result.sources), 5)

    def test_get_list_no_sources(self):
        result = self.actions.get_source_list(model.GetSourceListRequest("ApJ", 10, 0))

        self.assertEqual(len(result.sources), 0)
