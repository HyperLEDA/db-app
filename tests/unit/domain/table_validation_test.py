import unittest
from unittest import mock

from astropy import units as u

from app import entities
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

    def test_valid_table(self):
        request = presentation.ValidateTableRequest(42)

        self.layer0_repo.fetch_metadata.return_value = mock.MagicMock(
            column_descriptions=[
                entities.ColumnDescription(name="name", data_type="text", ucd="meta.id"),
                entities.ColumnDescription(name="ra", data_type="float", unit=u.Unit("hourangle"), ucd="pos.eq.ra"),
                entities.ColumnDescription(name="dec", data_type="float", unit=u.Unit("deg"), ucd="pos.eq.dec"),
            ]
        )

        response = self.manager.validate_table(request)

        self.assertEqual(response.validations, [])

    def test_invalid_table(self):
        request = presentation.ValidateTableRequest(42)

        self.layer0_repo.fetch_metadata.return_value = mock.MagicMock(
            column_descriptions=[
                entities.ColumnDescription(name="name", data_type="text", ucd="meta.id"),
                entities.ColumnDescription(name="ra", data_type="float", ucd="pos.eq.ra"),
                entities.ColumnDescription(name="dec", data_type="float", unit=u.Unit("deg"), ucd="pos.eq.dec"),
            ]
        )

        response = self.manager.validate_table(request)

        self.assertEqual(len(response.validations), 1)
