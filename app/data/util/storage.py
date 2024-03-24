from typing import Self

import psycopg


class _TransactionHolder:
    def __init__(self, connection: psycopg.Connection, tx: psycopg.Transaction | None) -> None:
        self.tx = tx
        self.connection = connection
        self.is_created = tx is None

    def __enter__(self) -> Self:
        if self.is_created:
            self.tx = self.connection.transaction()
            self.tx.__enter__()

        return self

    def __exit__(self, exc_type, exc_val: Exception | None, exc_tb) -> None:
        if self.is_created and self.tx is not None:
            self.tx.__exit__(exc_type, exc_val, exc_tb)


def get_or_create_transaction(
    connection: psycopg.Connection, tx: psycopg.Transaction | None = None
) -> _TransactionHolder:
    return _TransactionHolder(connection, tx)
