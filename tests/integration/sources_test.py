import unittest
from unittest import mock

import structlog

from app.data import repositories
from app.domain import model, usecases
from app.lib import auth, testing
from app.lib import clients as libclients


class SourcesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = testing.get_test_postgres_storage()

        logger = structlog.get_logger()
        cls.clients = libclients.Clients("")
        cls.clients.ads = mock.MagicMock()

        cls.actions = usecases.Actions(
            common_repo=repositories.CommonRepository(cls.storage.get_storage(), logger),
            layer0_repo=repositories.Layer0Repository(cls.storage.get_storage(), logger),
            layer1_repo=repositories.Layer1Repository(cls.storage.get_storage(), logger),
            queue_repo=None,
            authenticator=auth.NoopAuthenticator(),
            clients=cls.clients,
            storage_config=None,
            logger=logger,
        )

    def tearDown(self):
        self.storage.clear()

    def test_create_one_source_success(self):
        self.clients.ads.query_simple = mock.MagicMock(
            return_value=[
                {
                    "bibcode": "1992ApJ...400L...1W",
                    "author": ["Test author et al."],
                    "pubdate": "2000-03-00",
                    "title": ["Test research"],
                }
            ]
        )

        create_response = self.actions.create_source(model.CreateSourceRequest(bibcode="1992ApJ...400L...1W"))
        get_response = self.actions.get_source(model.GetSourceRequest(id=create_response.id))

        self.assertEqual(get_response.bibcode, "1992ApJ...400L...1W")
        self.assertEqual(get_response.authors, ["Test author et al."])
        self.assertEqual(get_response.year, 2000)
        self.assertEqual(get_response.title, "Test research")

    def test_data_from_ads_differs(self):
        self.clients.ads.query_simple = mock.MagicMock(
            return_value=[
                {
                    "bibcode": "1992ApJ...400L...1W",
                    "author": ["from_ads"],
                    "pubdate": "2000-03-00",
                    "title": ["from_ads"],
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
        self.assertEqual(get_response.authors, ["from_ads"])
        self.assertEqual(get_response.year, 2000)
        self.assertEqual(get_response.title, "from_ads")

    def test_create_two_sources_duplicate(self):
        self.clients.ads.query_simple = mock.MagicMock(
            return_value=[
                {
                    "bibcode": "2000ApJ...400L...1W",
                    "author": ["Test author et al."],
                    "pubdate": "2000-03-00",
                    "title": ["Test research"],
                }
            ]
        )

        _ = self.actions.create_source(model.CreateSourceRequest(bibcode="2000ApJ...400L...1W"))

        with self.assertRaises(Exception):
            _ = self.actions.create_source(model.CreateSourceRequest(bibcode="2000ApJ...400L...1W"))

    def test_get_non_existent_source_id(self):
        with self.assertRaises(Exception):
            _ = self.actions.get_source(model.GetSourceRequest(id=12321))

    def test_get_list_first_page_full(self):
        for i in range(25):
            self.clients.ads.query_simple = mock.MagicMock(
                return_value=[
                    {
                        "bibcode": f"20{i:02d}ApJ...401L...1W",
                        "author": ["Test author et al."],
                        "pubdate": "2000-03-00",
                        "title": [f"20{i:02d}ApJ...401L...1W"],
                    }
                ]
            )

            _ = self.actions.create_source(model.CreateSourceRequest(bibcode=f"20{i:02d}ApJ...401L...1W"))

        result = self.actions.get_source_list(model.GetSourceListRequest("ApJ", 10, 0))

        self.assertEqual(len(result.sources), 10)

    def test_get_filtered_titles(self):
        _ = self.actions.create_source(
            model.CreateSourceRequest(
                authors=["Test author et al."],
                year=2000,
                title="Test research",
            ),
        )

        _ = self.actions.create_source(
            model.CreateSourceRequest(
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
            self.clients.ads.query_simple = mock.MagicMock(
                return_value=[
                    {
                        "bibcode": f"20{i:02d}ApJ...402L...1W",
                        "author": ["Test author et al."],
                        "pubdate": "2000-03-00",
                        "title": [f"20{i:02d}ApJ...402L...1W"],
                    }
                ]
            )

            _ = self.actions.create_source(model.CreateSourceRequest(bibcode=f"20{i:02d}ApJ...402L...1W"))

        result = self.actions.get_source_list(model.GetSourceListRequest("ApJ", 10, 1))

        self.assertEqual(len(result.sources), 5)

    def test_get_list_no_sources(self):
        result = self.actions.get_source_list(model.GetSourceListRequest("ApJ", 10, 0))

        self.assertEqual(len(result.sources), 0)
