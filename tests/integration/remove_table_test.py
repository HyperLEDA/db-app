import unittest

import structlog

from app.data import repositories
from app.data.repositories.layer0.common import INTERNAL_ID_COLUMN_NAME
from app.domain import adminapi as domain
from app.lib import clients
from app.lib.storage import enums
from app.presentation import adminapi as presentation
from tests import lib


class RemoveTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()
        cls.storage = cls.pg_storage.get_storage()
        cls.manager = domain.TableUploadManager(
            repositories.CommonRepository(cls.storage, structlog.get_logger()),
            repositories.Layer0Repository(cls.storage, structlog.get_logger()),
            repositories.Layer1Repository(cls.storage, structlog.get_logger()),
            clients.get_mock_clients(),
        )
        cls.layer0_repo = repositories.Layer0Repository(cls.storage, structlog.get_logger())

    def tearDown(self) -> None:
        self.pg_storage.clear()

    def _mock_ads(self) -> None:
        publication = [
            {
                "bibcode": "2024arXiv240411942F",
                "author": ["test"],
                "pubdate": "2020-03-00",
                "title": ["test"],
            }
        ]
        lib.returns(self.manager.clients.ads.query_simple, publication)
        lib.returns(self.manager.clients.ads.query_simple, publication)

    def _create_minimal_table(self, table_name: str) -> None:
        self.manager.create_table(
            presentation.CreateTableRequest(
                table_name=table_name,
                columns=[
                    presentation.ColumnDescription(
                        name="objname", data_type=presentation.DatatypeEnum["str"], ucd="meta.id"
                    ),
                    presentation.ColumnDescription(
                        name="ra", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.ra", unit="h"
                    ),
                    presentation.ColumnDescription(
                        name="dec", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.dec", unit="h"
                    ),
                ],
                bibcode="2024arXiv240411942F",
                datatype=enums.DataType.REGULAR,
                description="",
            ),
        )

    def _add_dummy_rows(self, table_name: str) -> None:
        self.manager.add_data(
            presentation.AddDataRequest(
                table_name=table_name,
                data=[
                    {"ra": 1.0, "dec": 2.0},
                    {"ra": 3.0, "dec": 4.0},
                ],
            ),
        )

    def _registry_row_count(self, table_name: str) -> int:
        rows = self.storage.query(
            "SELECT COUNT(*)::int AS c FROM layer0.tables WHERE table_name = %s",
            params=[table_name],
        )
        return int(rows[0]["c"])

    def _record_count_for_table(self, table_name: str) -> int:
        rows = self.storage.query(
            """
            SELECT COUNT(*)::int AS c
            FROM layer0.records r
            JOIN layer0.tables t ON r.table_id = t.id
            WHERE t.table_name = %s
            """,
            params=[table_name],
        )
        return int(rows[0]["c"])

    def _raw_table_exists(self, table_name: str) -> bool:
        rows = self.storage.query(
            """
            SELECT COUNT(*)::int AS c
            FROM information_schema.tables
            WHERE table_schema = 'rawdata' AND table_name = %s
            """,
            params=[table_name],
        )
        return int(rows[0]["c"]) > 0

    def _raw_row_count(self, table_name: str) -> int:
        rows = self.storage.query(
            f"SELECT COUNT(*)::int AS c FROM rawdata.{table_name}",
        )
        return int(rows[0]["c"])

    def _get_record_ids(self, table_name: str) -> list[str]:
        raw_data = self.layer0_repo.fetch_raw_data(
            table_name=table_name,
            columns=[INTERNAL_ID_COLUMN_NAME],
        )
        return raw_data.data[INTERNAL_ID_COLUMN_NAME].tolist()

    def test_remove_table(self) -> None:
        self._mock_ads()
        self._create_minimal_table("table_a")
        self._create_minimal_table("table_b")
        self._add_dummy_rows("table_a")
        self._add_dummy_rows("table_b")

        self.assertTrue(self._raw_table_exists("table_a"))
        self.assertTrue(self._raw_table_exists("table_b"))
        self.assertEqual(self._registry_row_count("table_a"), 1)
        self.assertEqual(self._registry_row_count("table_b"), 1)
        self.assertEqual(self._record_count_for_table("table_a"), 2)
        self.assertEqual(self._record_count_for_table("table_b"), 2)

        record_ids = self._get_record_ids("table_a")
        with self.layer0_repo.with_tx():
            self.layer0_repo.remove_records("table_a", record_ids)
        with self.layer0_repo.with_tx():
            self.layer0_repo.drop_raw_table("table_a")

        self.assertFalse(self._raw_table_exists("table_a"))
        self.assertTrue(self._raw_table_exists("table_b"))
        self.assertEqual(self._registry_row_count("table_a"), 0)
        self.assertEqual(self._registry_row_count("table_b"), 1)
        self.assertEqual(self._record_count_for_table("table_a"), 0)
        self.assertEqual(self._record_count_for_table("table_b"), 2)
        self.assertEqual(self._raw_row_count("table_b"), 2)

    def test_remove_table_batched(self) -> None:
        self._mock_ads()
        self._create_minimal_table("table_a")
        self._add_dummy_rows("table_a")

        all_ids = self._get_record_ids("table_a")
        self.assertEqual(len(all_ids), 2)

        with self.layer0_repo.with_tx():
            self.layer0_repo.remove_records("table_a", all_ids[:1])

        self.assertEqual(self._record_count_for_table("table_a"), 1)
        self.assertEqual(self._raw_row_count("table_a"), 1)

        with self.layer0_repo.with_tx():
            self.layer0_repo.remove_records("table_a", all_ids[1:])

        self.assertEqual(self._record_count_for_table("table_a"), 0)
        self.assertEqual(self._raw_row_count("table_a"), 0)

        with self.layer0_repo.with_tx():
            self.layer0_repo.drop_raw_table("table_a")

        self.assertFalse(self._raw_table_exists("table_a"))
        self.assertEqual(self._registry_row_count("table_a"), 0)
