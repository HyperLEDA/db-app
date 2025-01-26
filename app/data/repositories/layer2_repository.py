import datetime

import structlog

from app.data import model
from app.domain.model.layer2.layer_2_model import Layer2Model
from app.domain.model.params.layer_2_query_param import Layer2QueryParam
from app.lib.storage import postgres

tables = {
    model.RawCatalog.ICRS: "layer2.icrs",
    model.RawCatalog.DESIGNATION: "layer2.designation",
}


class Layer2Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        self._storage = storage

    def get_last_update_time(self) -> datetime.datetime:
        return self._storage.query_one("SELECT dt FROM layer2.last_update").get("dt")

    def update_last_update_time(self, dt: datetime.datetime):
        self._storage.exec("UPDATE layer2.last_update SET dt = %s", params=[dt])

    def save_data(self, catalog: model.RawCatalog, objects: dict[int, model.CatalogObject]):
        table = tables[catalog]

        for obj in objects.values():
            data = obj.layer2_data()
            columns = list(data.keys())
            values = [data[column] for column in columns]

            query = f"""
            INSERT INTO {table} ({", ".join(columns)}) 
            VALUES ({",".join(["%s"] * len(columns))})
            """

            self._storage.exec(query, params=values)

    def query_data(self, param: Layer2QueryParam) -> list[Layer2Model]:
        return []

    def save_update_instances(self, instances: list[Layer2Model]):
        pass
