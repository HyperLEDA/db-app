import unittest
from unittest import mock

from astropy import units as u
from parameterized import param, parameterized

from app.data import model
from app.domain import adminapi as domain
from app.lib import clients
from app.presentation import adminapi as presentation


class TableValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.layer0_repo = mock.MagicMock()

        self.manager = domain.TableUploadManager(
            common_repo=mock.MagicMock(),
            layer0_repo=self.layer0_repo,
            clients=clients.get_mock_clients(),
        )

    @parameterized.expand(
        [
            param(
                "valid table",
                [
                    model.ColumnDescription(name="name", data_type="text", ucd="meta.id"),
                    model.ColumnDescription(name="ra", data_type="float", unit=u.Unit("hourangle"), ucd="pos.eq.ra"),
                    model.ColumnDescription(name="dec", data_type="float", unit=u.Unit("deg"), ucd="pos.eq.dec"),
                    model.ColumnDescription(name="redshift", data_type="float", ucd="src.redshift"),
                ],
                0,
            ),
            param(
                "one invalid validator",
                [
                    model.ColumnDescription(name="name", data_type="text", ucd="meta.id"),
                    model.ColumnDescription(name="ra", data_type="float", unit=u.Unit("kg"), ucd="pos.eq.ra"),
                    model.ColumnDescription(name="dec", data_type="float", unit=u.Unit("deg"), ucd="pos.eq.dec"),
                    model.ColumnDescription(name="redshift", data_type="float", ucd="src.redshift"),
                ],
                1,
            ),
            param(
                "two invalid validators",
                [
                    model.ColumnDescription(name="name", data_type="text"),
                    model.ColumnDescription(name="ra", data_type="float", unit=u.Unit("kg"), ucd="pos.eq.ra"),
                    model.ColumnDescription(name="dec", data_type="float", unit=u.Unit("deg"), ucd="pos.eq.dec"),
                    model.ColumnDescription(name="redshift", data_type="float", ucd="src.redshift"),
                ],
                2,
            ),
        ]
    )
    def test_validation(self, name: str, columns: list[model.ColumnDescription], expected_len: int):
        request = presentation.GetTableValidationRequest(42)

        self.layer0_repo.fetch_metadata.return_value = mock.MagicMock(column_descriptions=columns)

        response = self.manager.validate_table(request)

        self.assertEqual(len(response.validations), expected_len)
