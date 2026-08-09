import datetime
import unittest
import uuid

import pydantic
import structlog

from app.adminapi import presentation as adminapi
from app.adminapi.domain import pgc
from app.data import model, repositories
from app.lib.web import errors
from tests import lib


class MergePgcsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()
        cls.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.manager = pgc.PgcManager(cls.common_repo, cls.layer0_repo)

    def tearDown(self) -> None:
        self.pg_storage.clear()

    def _create_table(self, table_name: str) -> None:
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        self.layer0_repo.create_table(model.Layer0TableMeta(table_name, [], bib_id))

    def _register_with_pgcs(self, table_name: str, record_pgcs: dict[str, int]) -> None:
        self._create_table(table_name)
        record_ids = list(record_pgcs.keys())
        self.layer0_repo.register_records(table_name, record_ids)
        self.common_repo.register_pgcs(list(set(record_pgcs.values())))
        self.layer0_repo.upsert_pgc(dict(record_pgcs))

    def _pgc_for(self, record_id: str) -> int | None:
        row = self.pg_storage.storage.query_one(
            "SELECT pgc FROM layer0.records WHERE id = %s",
            params=[record_id],
        )
        return row["pgc"]

    def _modification_time(self, pgc_id: int) -> datetime.datetime:
        row = self.pg_storage.storage.query_one(
            "SELECT modification_time FROM common.pgc WHERE id = %s",
            params=[pgc_id],
        )
        return row["modification_time"]

    def test_merge_multiple_sources_onto_target(self) -> None:
        target_pgc = 100
        source_a = 200
        source_b = 300
        target_id = str(uuid.uuid4())
        source_a_id = str(uuid.uuid4())
        source_b_id = str(uuid.uuid4())
        self._register_with_pgcs(
            "merge_multi",
            {
                target_id: target_pgc,
                source_a_id: source_a,
                source_b_id: source_b,
            },
        )

        old_dt = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
        self.pg_storage.storage.exec(
            "UPDATE common.pgc SET modification_time = %s WHERE id = ANY(%s)",
            params=[old_dt, [target_pgc, source_a, source_b]],
        )

        response = self.manager.merge_pgcs(
            adminapi.MergePgcsRequest(target_pgc=target_pgc, source_pgcs=[source_a, source_b]),
        )

        self.assertEqual(response.target_pgc, target_pgc)
        self.assertEqual(response.merged_pgcs, [source_a, source_b])
        self.assertEqual(response.reassigned_records, 2)
        self.assertEqual(self._pgc_for(target_id), target_pgc)
        self.assertEqual(self._pgc_for(source_a_id), target_pgc)
        self.assertEqual(self._pgc_for(source_b_id), target_pgc)
        self.assertGreater(self._modification_time(target_pgc).replace(tzinfo=datetime.UTC), old_dt)
        self.assertGreater(self._modification_time(source_a).replace(tzinfo=datetime.UTC), old_dt)
        self.assertGreater(self._modification_time(source_b).replace(tzinfo=datetime.UTC), old_dt)

    def test_reject_target_in_sources(self) -> None:
        with self.assertRaises(pydantic.ValidationError):
            adminapi.MergePgcsRequest(target_pgc=100, source_pgcs=[100, 200])

    def test_reject_duplicate_sources(self) -> None:
        with self.assertRaises(pydantic.ValidationError):
            adminapi.MergePgcsRequest(target_pgc=100, source_pgcs=[200, 200])

    def test_reject_missing_target(self) -> None:
        source_pgc = 9_000_001
        missing_target = 9_000_002
        self.common_repo.register_pgcs([source_pgc])

        with self.assertRaises(errors.NotFoundError):
            self.manager.merge_pgcs(
                adminapi.MergePgcsRequest(target_pgc=missing_target, source_pgcs=[source_pgc]),
            )

    def test_reject_missing_source(self) -> None:
        target_pgc = 9_000_003
        missing_source = 9_000_004
        self.common_repo.register_pgcs([target_pgc])

        with self.assertRaises(errors.NotFoundError):
            self.manager.merge_pgcs(
                adminapi.MergePgcsRequest(target_pgc=target_pgc, source_pgcs=[missing_source]),
            )
