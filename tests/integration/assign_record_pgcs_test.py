import os
import subprocess
import time
import unittest
import uuid
from concurrent import futures

import requests
import structlog

from app.data import model, repositories
from app.domain.adminapi import crossmatch
from app.lib.storage import enums
from app.lib.web import errors
from app.presentation import adminapi
from tests import lib
from tests.lib import auth_seed

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class AssignRecordPgcsRepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()
        cls.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer1_repo = repositories.Layer1Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.layer2_repo = repositories.Layer2Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.manager = crossmatch.CrossmatchManager(cls.layer0_repo, cls.layer1_repo, cls.layer2_repo)

    def tearDown(self) -> None:
        self.pg_storage.clear()

    def _create_table(self, table_name: str) -> None:
        bib_id = self.common_repo.create_bibliography("123456", 2000, ["test"], "test")
        self.layer0_repo.create_table(model.Layer0TableMeta(table_name, [], bib_id))

    def _register(self, table_name: str, record_ids: list[str]) -> None:
        self._create_table(table_name)
        self.layer0_repo.register_records(table_name, record_ids)

    def _set_crossmatch(
        self,
        rows: list[tuple[str, enums.RecordTriageStatus, list[int]]],
    ) -> None:
        self.layer0_repo.set_crossmatch_results(rows)

    def _pgc_for(self, record_id: str) -> int | None:
        row = self.pg_storage.storage.query_one(
            "SELECT pgc FROM layer0.records WHERE id = %s",
            params=[record_id],
        )
        return row["pgc"]

    def test_submit_new_and_existing_records(self) -> None:
        table_name = "submit_happy"
        new_id = str(uuid.uuid4())
        existing_id = str(uuid.uuid4())
        existing_pgc = 4242
        self._register(table_name, [new_id, existing_id])
        self.common_repo.register_pgcs([existing_pgc])
        self._set_crossmatch(
            [
                (new_id, enums.RecordTriageStatus.RESOLVED, []),
                (existing_id, enums.RecordTriageStatus.RESOLVED, [existing_pgc]),
            ]
        )

        self.manager.assign_record_pgcs(adminapi.AssignRecordPgcsRequest(record_ids=[new_id, existing_id]))

        new_pgc = self._pgc_for(new_id)
        self.assertIsNotNone(new_pgc)
        self.assertEqual(self._pgc_for(existing_id), existing_pgc)
        self.assertNotEqual(new_pgc, existing_pgc)

    def test_reject_pending_records(self) -> None:
        table_name = "submit_pending"
        pending_id = str(uuid.uuid4())
        resolved_id = str(uuid.uuid4())
        self._register(table_name, [pending_id, resolved_id])
        self._set_crossmatch(
            [
                (pending_id, enums.RecordTriageStatus.PENDING, []),
                (resolved_id, enums.RecordTriageStatus.RESOLVED, []),
            ]
        )

        with self.assertRaises(errors.ConflictError) as ctx:
            self.manager.assign_record_pgcs(
                adminapi.AssignRecordPgcsRequest(record_ids=[pending_id, resolved_id]),
            )

        self.assertEqual(ctx.exception.count, 1)
        self.assertIn(pending_id, ctx.exception.sample_record_ids or [])
        self.assertIsNone(self._pgc_for(pending_id))
        self.assertIsNone(self._pgc_for(resolved_id))

    def test_reject_missing_crossmatch_row(self) -> None:
        table_name = "submit_missing"
        missing_id = str(uuid.uuid4())
        self._register(table_name, [missing_id])

        with self.assertRaises(errors.ConflictError) as ctx:
            self.manager.assign_record_pgcs(adminapi.AssignRecordPgcsRequest(record_ids=[missing_id]))

        self.assertEqual(ctx.exception.count, 1)
        self.assertIsNone(self._pgc_for(missing_id))

    def test_reject_collided_metadata(self) -> None:
        table_name = "submit_collided"
        collided_id = str(uuid.uuid4())
        self._register(table_name, [collided_id])
        self.common_repo.register_pgcs([10, 11])
        self._set_crossmatch(
            [(collided_id, enums.RecordTriageStatus.RESOLVED, [10, 11])],
        )

        with self.assertRaises(errors.ConflictError):
            self.manager.assign_record_pgcs(adminapi.AssignRecordPgcsRequest(record_ids=[collided_id]))

        self.assertIsNone(self._pgc_for(collided_id))

    def test_idempotent_retry(self) -> None:
        table_name = "submit_retry"
        record_id = str(uuid.uuid4())
        self._register(table_name, [record_id])
        self._set_crossmatch([(record_id, enums.RecordTriageStatus.RESOLVED, [])])

        request = adminapi.AssignRecordPgcsRequest(record_ids=[record_id])
        self.manager.assign_record_pgcs(request)
        first_pgc = self._pgc_for(record_id)
        self.assertIsNotNone(first_pgc)

        pgc_count_before = self.pg_storage.storage.query_one("SELECT COUNT(*)::int AS cnt FROM common.pgc")["cnt"]
        self.manager.assign_record_pgcs(request)
        pgc_count_after = self.pg_storage.storage.query_one("SELECT COUNT(*)::int AS cnt FROM common.pgc")["cnt"]

        self.assertEqual(self._pgc_for(record_id), first_pgc)
        self.assertEqual(pgc_count_before, pgc_count_after)


class AssignRecordPgcsAuthTest(unittest.TestCase):
    _login = "integration_assign_pgc_admin"
    _password = "integration-secret"

    @classmethod
    def setUpClass(cls) -> None:
        with futures.ThreadPoolExecutor() as group:
            pg_thread = group.submit(lib.TestPostgresStorage.get)
            port_thread = group.submit(lib.find_free_port)

        cls.pg_storage = pg_thread.result()
        cls.server_port = port_thread.result()

        auth_seed.seed_admin_user(cls.pg_storage.get_storage(), cls._login, cls._password)

        os.environ["SERVER_PORT"] = str(cls.server_port)
        os.environ["STORAGE_ENDPOINT"] = "localhost"
        os.environ["STORAGE_PORT"] = str(cls.pg_storage.port)
        os.environ["CLIENTS_ADS_TOKEN"] = "test"
        os.environ["AUTH_ENABLED"] = "true"

        cls.process = subprocess.Popen(
            [
                "uv",
                "run",
                "app",
                "adminapi",
                "-c",
                "configs/dev/adminapi.yaml",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                r = requests.get(f"http://127.0.0.1:{cls.server_port}/ping", timeout=1)
                if r.status_code == 200:
                    break
            except (requests.RequestException, OSError):
                pass
            time.sleep(0.3)
            if cls.process.poll() is not None and cls.process.returncode != 0:
                raise RuntimeError("adminapi process exited before becoming ready")
        else:
            cls.process.kill()
            raise RuntimeError("adminapi did not respond on /ping within 30s")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.kill()
        cls.process.wait()
        storage = cls.pg_storage.get_storage()
        storage.exec(
            "DELETE FROM private.tokens WHERE user_id IN (SELECT id FROM private.users WHERE login = %s)",
            params=[cls._login],
        )
        storage.exec("DELETE FROM private.users WHERE login = %s", params=[cls._login])

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server_port}/admin/api"

    def test_submit_without_auth(self) -> None:
        r = requests.post(
            f"{self.base}/v1/records/pgcs",
            json={"record_ids": [str(uuid.uuid4())]},
            timeout=5,
        )
        self.assertEqual(r.status_code, 401)

    def test_submit_with_admin_token(self) -> None:
        login_r = requests.post(
            f"{self.base}/v1/login",
            json={"username": self._login, "password": self._password},
            timeout=5,
        )
        self.assertEqual(login_r.status_code, 200)
        token = login_r.json()["data"]["token"]

        r = requests.post(
            f"{self.base}/v1/records/pgcs",
            headers={"Authorization": f"Bearer {token}"},
            json={"record_ids": [str(uuid.uuid4())]},
            timeout=5,
        )
        self.assertEqual(r.status_code, 409)
        body = r.json()
        self.assertEqual(body["code"], "conflict")
