import datetime
from typing import final

import structlog

from app.data import model, repositories
from app.lib import containers
from app.lib.storage import postgres
from app.tasks import interface

catalogs = [
    model.RawCatalog.ICRS,
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.REDSHIFT,
]


@final
class Layer2ImportTask(interface.Task):
    def __init__(self, batch_size: int = 1500) -> None:
        self.log = structlog.get_logger()
        self.batch_size = batch_size

    @classmethod
    def name(cls) -> str:
        return "layer2-import"

    def prepare(self, config: interface.Config):
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()

        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, self.log)
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, self.log)

    def run(self):
        last_update_dt = self.layer2_repository.get_last_update_time()

        self.log.info("Starting Layer 2 import", last_update=last_update_dt.ctime())

        for catalog in catalogs:
            for offset, new_objects in containers.read_batches(
                self.layer1_repository.get_new_observations,
                lambda data: len(data) == 0,
                0,
                lambda d, _: d[-1].pgc,
                last_update_dt,
                batch_size=self.batch_size,
                catalog=catalog,
            ):
                self.log.info(
                    "Processing batch",
                    catalog=catalog.value,
                    last_pgc=offset,
                    batch_size=len(new_objects),
                )

                objects_by_catalog = containers.group_by(
                    new_objects, key_func=lambda obj: obj.observation.catalog_object.catalog()
                )
                aggregated_objects: list[model.Layer2CatalogObject] = []

                for catalog, objects in objects_by_catalog.items():
                    objects_by_pgc = containers.group_by(objects, key_func=lambda obj: obj.pgc)

                    for pgc, objects in objects_by_pgc.items():
                        catalog_objects = [obj.observation.catalog_object for obj in objects]
                        aggregated_objects.append(
                            model.Layer2CatalogObject(
                                pgc, model.get_catalog_object_type(catalog).aggregate(catalog_objects)
                            )
                        )
                self.layer2_repository.save_data(aggregated_objects)

            self.log.info("Updated catalog", catalog=catalog.value)

        self.layer2_repository.update_last_update_time(datetime.datetime.now(tz=datetime.UTC))
        self.log.info("Layer 2 import completed", last_update=last_update_dt.ctime())

    def cleanup(self):
        self.pg_storage.disconnect()
