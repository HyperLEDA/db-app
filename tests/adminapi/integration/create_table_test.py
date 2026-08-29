import unittest

import structlog

from app.adminapi import clients, domain, repository
from app.adminapi.domain.mock import get_mock_table_stats_cache
from app.lib.storage import enums
from app.specs import adminapi
from tests import lib


class CreateTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get(enums.PG_ENUM_REGISTRY)

        cls.repo = repository.Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.source_manager = domain.SourceManager(cls.repo)
        cls.upload_manager = domain.TableUploadManager(
            cls.repo,
            clients.get_mock_clients(),
            get_mock_table_stats_cache(),
        )

    def tearDown(self):
        self.pg_storage.clear()

    def test_create_table(self):
        source_code = self.source_manager.create_source(
            adminapi.CreateSourceRequest(title="title", authors=["author"], year=2022)
        ).code

        self.upload_manager.create_table(
            adminapi.CreateTableRequest(
                table_name="table_name",
                columns=[
                    adminapi.ColumnDescription(name="name", data_type=adminapi.DatatypeEnum["text"], ucd="meta.id"),
                    adminapi.ColumnDescription(
                        name="ra", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.ra", unit="rad"
                    ),
                    adminapi.ColumnDescription(
                        name="dec", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.dec", unit="rad"
                    ),
                    adminapi.ColumnDescription(
                        name="redshift", data_type=adminapi.DatatypeEnum["float"], ucd="src.redshift"
                    ),
                ],
                bibcode=source_code,
                datatype=enums.DataType.REGULAR,
                description="description",
            )
        )

    def test_create_table_with_patch(self):
        source_code = self.source_manager.create_source(
            adminapi.CreateSourceRequest(title="title", authors=["author"], year=2022)
        ).code
        table_name = "table_name"

        _, created = self.upload_manager.create_table(
            adminapi.CreateTableRequest(
                table_name=table_name,
                columns=[
                    adminapi.ColumnDescription(name="name", data_type=adminapi.DatatypeEnum["text"]),
                    adminapi.ColumnDescription(name="ra", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.ra"),
                    adminapi.ColumnDescription(
                        name="dec", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.dec", unit="rad"
                    ),
                ],
                bibcode=source_code,
                datatype=enums.DataType.REGULAR,
                description="description",
            )
        )

        self.assertTrue(created)

        self.upload_manager.patch_table(
            adminapi.PatchTableRequest(
                table_name=table_name,
                description="updated table description",
                datatype=enums.DataType.PRELIMINARY,
                columns={
                    "name": adminapi.PatchColumnSpec(ucd="meta.id"),
                    "ra": adminapi.PatchColumnSpec(unit="hourangle"),
                },
            ),
        )

        meta = self.upload_manager.get_table(adminapi.GetTableRequest(table_name=table_name))
        self.assertEqual(meta.description, "updated table description")
        self.assertEqual(meta.meta["datatype"], enums.DataType.PRELIMINARY)
        self.assertEqual(meta.meta["status"], enums.TableStatus.INITIATED)

        self.upload_manager.patch_table(
            adminapi.PatchTableRequest(
                table_name=table_name,
                status=enums.TableStatus.ARCHIVED,
            ),
        )

        meta = self.upload_manager.get_table(adminapi.GetTableRequest(table_name=table_name))
        self.assertEqual(meta.meta["status"], enums.TableStatus.ARCHIVED)

        default_list = self.upload_manager.get_table_list(adminapi.GetTableListRequest(query=table_name))
        self.assertEqual(default_list.tables, [])

        archived_list = self.upload_manager.get_table_list(
            adminapi.GetTableListRequest(
                query=table_name,
                statuses=[enums.TableStatus.ARCHIVED],
            )
        )
        self.assertEqual(len(archived_list.tables), 1)
        self.assertEqual(archived_list.tables[0].name, table_name)
        self.assertEqual(archived_list.tables[0].status, enums.TableStatus.ARCHIVED)
