import unittest
from unittest import mock

import structlog

from app.data import repositories
from app.domain import model, usecases
from app.lib import auth, testing


class SourcesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = testing.get_test_postgres_storage()

        logger = structlog.get_logger()

        cls.actions = usecases.Actions(
            common_repo=repositories.CommonRepository(cls.storage.get_storage(), logger),
            layer0_repo=repositories.Layer0Repository(cls.storage.get_storage(), logger),
            layer1_repo=repositories.Layer1Repository(cls.storage.get_storage(), logger),
            queue_repo=None,
            authenticator=auth.NoopAuthenticator(),
            storage_config=None,
            logger=logger,
        )

    def tearDown(self):
        self.storage.clear()

    @mock.patch("astroquery.nasa_ads.ADSClass")
    def test_create_one_source_success(self, ads_mock):
        ads_mock.return_value.query_simple = mock.MagicMock(
            return_value=[
                {
                    "bibcode": "1992ApJ...400L...1W",
                    "author": ["Test author et al."],
                    "pubdate": "2000-03-00",
                    "title": ["Test research"],
                }
            ]
        )

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

    @mock.patch("astroquery.nasa_ads.ADSClass")
    def test_data_from_ads_differs(self, ads_mock):
        ads_mock.return_value.query_simple = mock.MagicMock(
            return_value=[
                {
                    "bibcode": "1992ApJ...400L...1W",
                    "author": ["Test author et al."],
                    "pubdate": "2000-03-00",
                    "title": ["Test research"],
                }
            ]
        )

        create_response = self.actions.create_source(
            model.CreateSourceRequest(
                bibcode="1992ApJ...400L...1W",
                authors=["test"],
                year=2001,
                title="test",
            ),
        )
        get_response = self.actions.get_source(model.GetSourceRequest(id=create_response.id))

        self.assertEqual(get_response.bibcode, "1992ApJ...400L...1W")
        self.assertEqual(get_response.authors, ["Test author et al."])
        self.assertEqual(get_response.year, 2000)
        self.assertEqual(get_response.title, "Test research")

    @mock.patch("astroquery.nasa_ads.ADSClass")
    def test_create_two_sources_duplicate(self, ads_mock):
        ads_mock.return_value.query_simple = mock.MagicMock(
            return_value=[
                {
                    "bibcode": "2000ApJ...400L...1W",
                    "author": ["Test author et al."],
                    "pubdate": "2000-03-00",
                    "title": ["Test research"],
                }
            ]
        )

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

    @mock.patch("astroquery.nasa_ads.ADSClass")
    def test_get_list_first_page_full(self, ads_mock):
        for i in range(25):
            ads_mock.return_value.query_simple = mock.MagicMock(
                return_value=[
                    {
                        "bibcode": f"20{i:02d}ApJ...401L...1W",
                        "author": ["Test author et al."],
                        "pubdate": "2000-03-00",
                        "title": [f"20{i:02d}ApJ...401L...1W"],
                    }
                ]
            )

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

    @mock.patch("astroquery.nasa_ads.ADSClass")
    def test_get_filtered_titles(self, ads_mock):
        ads_mock.return_value.query_simple = mock.MagicMock(
            return_value=[
                {
                    "bibcode": "2001ApJ...401L...1W",
                    "author": ["Test author et al."],
                    "pubdate": "2000-03-00",
                    "title": ["Test research"],
                }
            ]
        )

        _ = self.actions.create_source(
            model.CreateSourceRequest(
                bibcode="2001ApJ...401L...1W",
                authors=["Test author et al."],
                year=2000,
                title="Test research",
            ),
        )

        ads_mock.return_value.query_simple = mock.MagicMock(
            return_value=[
                {
                    "bibcode": "2002ApJ...401L...1W",
                    "author": ["Test author et al."],
                    "pubdate": "2000-03-00",
                    "title": ["Test important research"],
                }
            ]
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

    @mock.patch("astroquery.nasa_ads.ADSClass")
    def test_get_list_second_page_not_full(self, ads_mock):
        for i in range(15):
            ads_mock.return_value.query_simple = mock.MagicMock(
                return_value=[
                    {
                        "bibcode": f"20{i:02d}ApJ...402L...1W",
                        "author": ["Test author et al."],
                        "pubdate": "2000-03-00",
                        "title": [f"20{i:02d}ApJ...402L...1W"],
                    }
                ]
            )

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
