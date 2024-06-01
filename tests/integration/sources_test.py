import unittest
from unittest import mock

import structlog

from app import commands
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
            commands.Depot(
                repositories.CommonRepository(cls.storage.get_storage(), logger),
                repositories.Layer0Repository(cls.storage.get_storage(), logger),
                None,
                auth.NoopAuthenticator(),
                cls.clients,
            ),
            storage_config=None,
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
