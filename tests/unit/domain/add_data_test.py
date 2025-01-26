import unittest

from app import schema
from app.commands.adminapi import depot
from app.domain import actions


class AddDataTest(unittest.TestCase):
    def setUp(self):
        self.depot = depot.get_mock_depot()

    def test_add_data(self):
        request = schema.AddDataRequest(
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

        request = self.depot.layer0_repo.insert_raw_data.call_args

        self.assertListEqual(list(request.args[0].data["test"]), ["row", "row2"])
        self.assertListEqual(list(request.args[0].data["number"]), [41, 43])
        self.assertListEqual(
            list(request.args[0].data["hyperleda_internal_id"]),
            ["b595be2e-b143-7a9e-3428-0e0f01e5f674", "d7a02ed8-6c59-e5e8-2a7b-346150685abf"],
        )

    def test_add_data_identical_rows(self):
        request = schema.AddDataRequest(
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

        request = self.depot.layer0_repo.insert_raw_data.call_args

        self.assertListEqual(list(request.args[0].data["test"]), ["row"])
        self.assertListEqual(list(request.args[0].data["number"]), [41])
