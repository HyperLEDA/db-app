import os
import subprocess
import time
import unittest
from concurrent import futures

import requests
import structlog

from tests import lib
from tests.lib import auth_seed

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class AdminAPIAuthTest(unittest.TestCase):
    _login = "integration_auth_admin"
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
        os.environ["STORAGE_PORT"] = str(cls.pg_storage.port)
        os.environ["CLIENTS_ADS_TOKEN"] = "test"

        logger.info("starting adminapi for auth tests", port=cls.server_port)

        cls.process = subprocess.Popen(
            [
                "uv",
                "run",
                "app",
                "adminapi",
                "-c",
                "configs/test/adminapi.yaml",
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
            "DELETE FROM common.tokens WHERE user_id IN (SELECT id FROM common.users WHERE login = %s)",
            params=[cls._login],
        )
        storage.exec("DELETE FROM common.users WHERE login = %s", params=[cls._login])

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server_port}/admin/api"

    def test_get_public(self):
        r = requests.get(f"{self.base}/v1/tables", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_post_without_auth(self):
        r = requests.post(
            f"{self.base}/v1/source",
            json={"title": "t", "authors": ["A"], "year": 2020},
            timeout=5,
        )
        self.assertEqual(r.status_code, 401)

    def test_patch_without_auth(self):
        r = requests.patch(
            f"{self.base}/v1/table",
            json={"table_name": "nope", "columns": {}},
            timeout=5,
        )
        self.assertEqual(r.status_code, 401)

    def test_login_wrong_password(self):
        r = requests.post(
            f"{self.base}/v1/login",
            json={"username": self._login, "password": "wrong"},
            timeout=5,
        )
        self.assertEqual(r.status_code, 401)

    def test_login_then_post_logout_relogin_second_invalidates_first(self):
        r_login = requests.post(
            f"{self.base}/v1/login",
            json={"username": self._login, "password": self._password},
            timeout=5,
        )
        self.assertEqual(r_login.status_code, 200)
        token1 = r_login.json()["data"]["token"]

        r_login2 = requests.post(
            f"{self.base}/v1/login",
            json={"username": self._login, "password": self._password},
            timeout=5,
        )
        self.assertEqual(r_login2.status_code, 200)
        token2 = r_login2.json()["data"]["token"]

        r_old = requests.post(
            f"{self.base}/v1/source",
            headers={"Authorization": f"Bearer {token1}"},
            json={"title": "Old token", "authors": ["B"], "year": 2019},
            timeout=5,
        )
        self.assertEqual(r_old.status_code, 401)

        r_ok = requests.post(
            f"{self.base}/v1/source",
            headers={"Authorization": f"Bearer {token2}"},
            json={"title": "New token", "authors": ["C"], "year": 2021},
            timeout=5,
        )
        self.assertEqual(r_ok.status_code, 200)

        r_out = requests.post(
            f"{self.base}/v1/logout",
            headers={"Authorization": f"Bearer {token2}"},
            json={},
            timeout=5,
        )
        self.assertEqual(r_out.status_code, 200)

        r_after = requests.post(
            f"{self.base}/v1/source",
            headers={"Authorization": f"Bearer {token2}"},
            json={"title": "After logout", "authors": ["D"], "year": 2022},
            timeout=5,
        )
        self.assertEqual(r_after.status_code, 401)
