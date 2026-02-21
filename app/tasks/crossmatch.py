import uuid
from typing import final

import structlog

from app.data import model, repositories
from app.data.repositories import layer2
from app.domain.unification import crossmatch
from app.lib.storage import postgres
from app.tasks import interface
from plugins.loader import discover_matchers, discover_solvers

test_selector_config = {
    "type": "or",
    "filters": [
        {"type": "coordinates_in_radius", "radius": 30 / 60 / 60},
    ],
}

test_matcher_config = {
    "type": "and",
    "matcher1": {"type": "circle", "radius_arcsec": 20},
    "matcher2": {
        "type": "ignore_no_redshift",
        "matcher": {"type": "velocity_close", "velocity_variance": 1000},
    },
}

test_solver_config = {
    "type": "or",
    "solver1": {"type": "existing_only_one_above_threshold", "threshold": 0.99},
    "solver2": {"type": "new_all_below_threshold", "threshold": 0.01},
}


@final
class CrossmatchTask(interface.Task):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        table_name: str,
        batch_size: int = 500,
        workers: int = 8,
    ) -> None:
        self.table_name = table_name
        self.batch_size = batch_size
        self.workers = workers
        self.log = logger

    @classmethod
    def name(cls) -> str:
        return "crossmatch"

    def prepare(self, config: interface.Config):
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()

        self.layer0_repo = repositories.Layer0Repository(self.pg_storage, self.log)
        self.layer1_repo = repositories.Layer1Repository(self.pg_storage, self.log)
        self.layer2_repo = repositories.Layer2Repository(self.pg_storage, self.log)

        self.log.debug("Loading cross-identification plugins")
        matchers = discover_matchers("plugins/matchers")
        solvers = discover_solvers("plugins/solvers")

        self.selector = crossmatch.create_selector(test_selector_config, layer2.AVAILABLE_FILTERS)
        self.matcher = crossmatch.create_matcher(test_matcher_config, matchers)
        self.solver = crossmatch.create_solver(test_solver_config, solvers)

    def run(self):
        ctx = {"table_name": self.table_name}

        offset = None
        new_count = 0
        existing_count = 0
        collision_count = 0

        while True:
            records = self.layer1_repo.query_records(
                catalogs=[model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION, model.RawCatalog.REDSHIFT],
                table_name=self.table_name,
                offset=offset,
                limit=self.batch_size,
            )
            if len(records) == 0:
                break

            search_params = {}
            search_types = {}

            for record in records:
                icrs_obj = record.get(model.ICRSCatalogObject)
                if icrs_obj is not None:
                    search_params[record.id] = self.selector.extract_search_params(record.data)
                    search_types[search_params[record.id].name()] = self.selector

            layer2_results = self.layer2_repo.query_batch(
                catalogs=[model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION],
                search_types=search_types,
                search_params=search_params,
                limit=len(records) * 100,  # Allow multiple matches per object
                offset=0,
            )

            results: dict[str, model.CIResult] = {}

            for record in records:
                layer2_objects = layer2_results.get(record.id, [])
                probabilities: list[tuple[model.Layer2Object, float]] = []

                for layer2_object in layer2_objects:
                    probabilities.append((layer2_object, self.matcher(record, layer2_object)))

                result = self.solver(probabilities)
                results[record.id] = result

                if isinstance(result, model.CIResultObjectNew):
                    new_count += 1
                elif isinstance(result, model.CIResultObjectExisting):
                    existing_count += 1
                elif isinstance(result, model.CIResultObjectCollision):
                    collision_count += 1

            self.layer0_repo.add_crossmatch_result(results)

            offset = records[-1].id

            batch_new = sum(1 for r in results.values() if isinstance(r, model.CIResultObjectNew))
            batch_existing = sum(1 for r in results.values() if isinstance(r, model.CIResultObjectExisting))
            batch_collision = sum(1 for r in results.values() if isinstance(r, model.CIResultObjectCollision))
            total = new_count + existing_count + collision_count
            last_uuid = uuid.UUID(record.id or "00000000-0000-0000-0000-000000000000")
            max_uuid = uuid.UUID("FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF")

            self.log.info(
                "Completed batch",
                layer1_selected=len(records),
                layer2_selected=len(layer2_results),
                batch_new_count=batch_new,
                batch_existing_count=batch_existing,
                batch_collision_count=batch_collision,
                new=f"{new_count / total * 100:.01f}%",
                existing=f"{existing_count / total * 100:.01f}%",
                collision=f"{collision_count / total * 100:.01f}%",
                total=total,
                very_approximate_progress=f"{last_uuid.int / max_uuid.int * 100:.03f}%",
                **ctx,
            )

    def cleanup(self):
        self.pg_storage.disconnect()
