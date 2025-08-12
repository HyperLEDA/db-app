import unittest

import structlog

from app.data import repositories
from app.domain import adminapi as domain
from app.lib import clients
from app.lib.storage import enums
from app.presentation import adminapi as presentation
from tests import lib


class CreateTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()

        cls.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())

        cls.source_manager = domain.SourceManager(cls.common_repo)
        cls.upload_manager = domain.TableUploadManager(cls.common_repo, cls.layer0_repo, clients.get_mock_clients())

    def tearDown(self):
        self.pg_storage.clear()

    def test_create_table(self):
        source_code = self.source_manager.create_source(
            presentation.CreateSourceRequest(title="title", authors=["author"], year=2022)
        ).code

        response, created = self.upload_manager.create_table(
            presentation.CreateTableRequest(
                table_name="table_name",
                columns=[
                    presentation.ColumnDescription(
                        name="name", data_type=presentation.DatatypeEnum["text"], ucd="meta.id"
                    ),
                    presentation.ColumnDescription(
                        name="ra", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.ra", unit="rad"
                    ),
                    presentation.ColumnDescription(
                        name="dec", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.dec", unit="rad"
                    ),
                    presentation.ColumnDescription(
                        name="redshift", data_type=presentation.DatatypeEnum["float"], ucd="src.redshift"
                    ),
                ],
                bibcode=source_code,
                datatype=enums.DataType.REGULAR,
                description="description",
            )
        )

    def test_create_table_with_patch(self):
        source_code = self.source_manager.create_source(
            presentation.CreateSourceRequest(title="title", authors=["author"], year=2022)
        ).code
        table_name = "table_name"

        response, created = self.upload_manager.create_table(
            presentation.CreateTableRequest(
                table_name=table_name,
                columns=[
                    presentation.ColumnDescription(name="name", data_type=presentation.DatatypeEnum["text"]),
                    presentation.ColumnDescription(
                        name="ra", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.ra"
                    ),
                    presentation.ColumnDescription(
                        name="dec", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.dec", unit="rad"
                    ),
                ],
                bibcode=source_code,
                datatype=enums.DataType.REGULAR,
                description="description",
            )
        )

        self.assertTrue(created)

        self.upload_manager.patch_table(
            presentation.PatchTableRequest(
                table_name=table_name,
                actions=[
                    presentation.PatchTableActionTypeChangeUCD(column="name", ucd="meta.id"),
                    presentation.PatchTableActionTypeChangeUnit(column="ra", unit="hourangle"),
                ],
            ),
        )
