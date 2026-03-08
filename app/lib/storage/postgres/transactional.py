from contextlib import contextmanager

from app.lib.storage import postgres


class TransactionalPGRepository:
    def __init__(self, storage: postgres.PgStorage) -> None:
        self._storage = storage

    @contextmanager
    def with_tx(self):
        with self._storage.get_pool().connection() as conn:
            self._storage.set_thread_conn(conn)
            try:
                with conn.transaction():
                    yield
            finally:
                self._storage.set_thread_conn(None)
