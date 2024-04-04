import abc

import psycopg


class Transactional(abc.ABC):
    # TODO: use some custom transaction class instead of psycopg's
    def with_tx(self) -> psycopg.Transaction:
        raise NotImplementedError("not implemented")
