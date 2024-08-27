import unittest
from unittest import mock

from app import commands
from app.domain import actions
from app.domain import model as domain_model
from app.lib import auth


class AddDataTest(unittest.TestCase):
    def setUp(self):
        self.common_repo_mock = mock.MagicMock()
        self.layer0_repo_mock = mock.MagicMock()
        self.queue_repo_mock = mock.MagicMock()
        self.clients_mock = mock.MagicMock()
        self.ads_mock = mock.MagicMock()
        self.clients_mock.ads_client = self.ads_mock

        depot = commands.Depot(
            self.common_repo_mock,
            self.layer0_repo_mock,
            mock.MagicMock(),
            mock.MagicMock(),
            self.queue_repo_mock,
            auth.NoopAuthenticator(),
            self.clients_mock,
        )

        self.depot = depot

    def test_add_data(self):
        request = domain_model.AddDataRequest(
            42,
            data=[
                {
                    "test": "row",
                    "number": 41,
                },
                {
                    "test": "row2",
                    "number": 43,
                },
            ],
        )

        _ = actions.add_data(self.depot, request)

        request = self.layer0_repo_mock.insert_raw_data.call_args

        self.assertListEqual(list(request.args[0].data["test"]), ["row", "row2"])
        self.assertListEqual(list(request.args[0].data["number"]), [41, 43])
        self.assertListEqual(
            list(request.args[0].data["hyperleda_internal_id"]),
            ["b595be2e-b143-7a9e-3428-0e0f01e5f674", "d7a02ed8-6c59-e5e8-2a7b-346150685abf"],
        )

    def test_add_data_identical_rows(self):
        request = domain_model.AddDataRequest(
            42,
            data=[
                {
                    "test": "row",
                    "number": 41,
                },
                {
                    "test": "row",
                    "number": 41,
                },
            ],
        )

        _ = actions.add_data(self.depot, request)

        request = self.layer0_repo_mock.insert_raw_data.call_args

        self.assertListEqual(list(request.args[0].data["test"]), ["row"])
        self.assertListEqual(list(request.args[0].data["number"]), [41])
