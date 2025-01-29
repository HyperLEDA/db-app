import datetime
from typing import final

import structlog

from app.commands.importer import config
from app.data import model, repositories
from app.lib import commands, containers
from app.lib.storage import postgres

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class ImporterCommand(commands.Command):
    def __init__(self, config_path: str) -> None:
        self.config_path = config_path

    def prepare(self):
        self.config = config.parse_config(self.config_path)

        self.pg_storage = postgres.PgStorage(self.config.storage, log)
        self.pg_storage.connect()

        self.layer1_repository = repositories.Layer1Repository(self.pg_storage, log)
        self.layer2_repository = repositories.Layer2Repository(self.pg_storage, log)

    def run(self):
        # 1. for each catalog on layer 1 collect all objects that were modified
        # since the last import: collect(dt) -> dict[pgc, UnaggregatedInfo]
        # 2. for each pgc aggregate all objects: aggregate(pgc, dict[pgc, UnaggregatedInfo]) -> ObjectInfo
        # 3. write objects to the storage: write(objects: dict[pgc, ObjectInfo]) -> None

        last_update_dt = self.layer2_repository.get_last_update_time()
        new_objects = self.layer1_repository.get_new_objects(last_update_dt)

        objects_by_catalog = containers.group_by(new_objects, key_func=lambda obj: obj.catalog())
        aggregated_objects = []

        for catalog, objects in objects_by_catalog.items():
            objects_by_pgc = containers.group_by(objects, key_func=lambda obj: obj.pgc())

            for _, objects in objects_by_pgc.items():
                aggregated_objects.append(model.get_catalog_object_type(catalog).aggregate(objects))

        with self.layer2_repository.with_tx():
            self.layer2_repository.save_data(aggregated_objects)
            self.layer2_repository.update_last_update_time(datetime.datetime.now(tz=datetime.UTC))

    def cleanup(self):
        self.pg_storage.disconnect()
