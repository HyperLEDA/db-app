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
        os.environ["STORAGE_ENDPOINT"] = "localhost"
        os.environ["STORAGE_PORT"] = str(cls.pg_storage.port)
        os.environ["CLIENTS_ADS_TOKEN"] = "test"
        os.environ["AUTH_ENABLED"] = "true"

        logger.info("starting adminapi for auth tests", port=cls.server_port)

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

    def _login_and_get_token(self) -> str:
        r = requests.post(
            f"{self.base}/v1/login",
            json={"username": self._login, "password": self._password},
            timeout=5,
        )
        self.assertEqual(r.status_code, 200)
        return r.json()["data"]["token"]

    def _assert_token_works(self, token: str) -> None:
        r = requests.post(
            f"{self.base}/v1/source",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "t", "authors": ["A"], "year": 2020},
            timeout=5,
        )
        self.assertEqual(r.status_code, 200)

    def _assert_token_rejected(self, token: str) -> None:
        r = requests.post(
            f"{self.base}/v1/source",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "t", "authors": ["A"], "year": 2020},
            timeout=5,
        )
        self.assertEqual(r.status_code, 401)

    def test_up_to_three_tokens_are_valid(self):
        token1 = self._login_and_get_token()
        token2 = self._login_and_get_token()
        token3 = self._login_and_get_token()

        self._assert_token_works(token1)
        self._assert_token_works(token2)
        self._assert_token_works(token3)

    def test_fourth_token_invalidates_earliest(self):
        token1 = self._login_and_get_token()
        token2 = self._login_and_get_token()
        token3 = self._login_and_get_token()
        token4 = self._login_and_get_token()

        self._assert_token_rejected(token1)
        self._assert_token_works(token2)
        self._assert_token_works(token3)
        self._assert_token_works(token4)

    def test_logout_revokes_token(self):
        token = self._login_and_get_token()

        r_out = requests.post(
            f"{self.base}/v1/logout",
            headers={"Authorization": f"Bearer {token}"},
            json={},
            timeout=5,
        )
        self.assertEqual(r_out.status_code, 200)

        self._assert_token_rejected(token)
