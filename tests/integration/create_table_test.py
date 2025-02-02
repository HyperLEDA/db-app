import unittest

import structlog
from astropy import units as u

from app.data import repositories
from app.domain import adminapi as domain
from app.lib import clients, testing
from app.presentation import adminapi as presentation


class CreateTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = testing.get_test_postgres_storage()

        cls.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())

        cls.source_manager = domain.SourceManager(cls.common_repo)
        cls.upload_manager = domain.TableUploadManager(cls.common_repo, cls.layer0_repo, clients.get_mock_clients())

    def tearDown(self):
        self.pg_storage.clear()

    def test_create_table_no_validation(self):
        source_code = self.source_manager.create_source(
            presentation.CreateSourceRequest("title", ["author"], 2022)
        ).code

        response, created = self.upload_manager.create_table(
            presentation.CreateTableRequest(
                "table_name",
                [
                    presentation.ColumnDescription("name", "text", ucd="meta.id"),
                    presentation.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit=u.rad),
                    presentation.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit=u.rad),
                ],
                source_code,
                "regular",
                "description",
            )
        )

        validation_result = self.upload_manager.validate_table(presentation.GetTableValidationRequest(response.id))

        self.assertTrue(created)
        self.assertEqual(len(validation_result.validations), 0)

    def test_create_table_validation(self):
        source_code = self.source_manager.create_source(
            presentation.CreateSourceRequest("title", ["author"], 2022)
        ).code

        response, created = self.upload_manager.create_table(
            presentation.CreateTableRequest(
                "table_name",
                [
                    presentation.ColumnDescription("name", "text"),
                    presentation.ColumnDescription("ra", "float", ucd="pos.eq.ra"),
                    presentation.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit=u.rad),
                ],
                source_code,
                "regular",
                "description",
            )
        )

        self.assertTrue(created)

        validation_result = self.upload_manager.validate_table(presentation.GetTableValidationRequest(response.id))
        self.assertEqual(len(validation_result.validations), 2)

        self.upload_manager.patch_table(
            presentation.PatchTableRequest(
                response.id,
                [
                    presentation.PatchTableActionTypeChangeUCD("name", "meta.id"),
                    presentation.PatchTableActionTypeChangeUnit("ra", "hourangle"),
                ],
            ),
        )

        validation_result = self.upload_manager.validate_table(presentation.GetTableValidationRequest(response.id))
        self.assertEqual(len(validation_result.validations), 0)
