from contextlib import contextmanager

from app.lib.storage import postgres


class TransactionalPGRepository:
    def __init__(self, storage: postgres.PgStorage) -> None:
        self._storage = storage

    @contextmanager
    def with_tx(self):
        conn = self._storage.get_connection()
        try:
            with conn.transaction():
                yield
        except Exception as e:
            raise e
