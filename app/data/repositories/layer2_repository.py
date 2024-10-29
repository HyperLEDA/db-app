import structlog

from app.domain.model.layer2.layer_2_model import Layer2Model
from app.domain.model.params.layer_2_query_param import Layer2QueryParam
from app.lib.storage import postgres


class Layer2Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        self._storage = storage

    def query_data(self, param: Layer2QueryParam) -> list[Layer2Model]:
        return []

    def save_update_instances(self, instances: list[Layer2Model]):
        pass
