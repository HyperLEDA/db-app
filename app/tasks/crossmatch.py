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
        {"type": "coordinates_in_radius", "radius": 100 / 60 / 60},
    ],
}

test_matcher_config = {
    "type": "and",
    "matcher1": {
        "type": "and",
        "matcher1": {"type": "circle", "radius_arcsec": 100},
        "matcher2": {"type": "ignore_no_name", "matcher": {"type": "levenshtein", "max_distance": 5}},
    },
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
    def __init__(self, table_name: str, batch_size: int = 500, workers: int = 8) -> None:
        self.table_name = table_name
        self.batch_size = batch_size
        self.workers = workers
        self.log = structlog.get_logger()

    @classmethod
    def name(cls) -> str:
        return "crossmatch"

    def prepare(self, config: interface.Config):
        self.pg_storage = postgres.PgStorage(config.storage, self.log)
        self.pg_storage.connect()

        self.layer0_repo = repositories.Layer0Repository(self.pg_storage, self.log)
        self.layer2_repo = repositories.Layer2Repository(self.pg_storage, self.log)

        self.log.info("Loading cross-identification plugins")
        matchers = discover_matchers("plugins/matchers")
        solvers = discover_solvers("plugins/solvers")

        self.selector = crossmatch.create_selector(test_selector_config, layer2.AVAILABLE_FILTERS)
        self.matcher = crossmatch.create_matcher(test_matcher_config, matchers)
        self.solver = crossmatch.create_solver(test_solver_config, solvers)

        self.log.info("matchers", lst=matchers.keys())
        self.log.info("solvers", lst=solvers.keys())

    def run(self):
        table_meta = self.layer0_repo.fetch_metadata_by_name(self.table_name)
        if table_meta.table_id is None:
            raise RuntimeError(f"Table {self.table_name} has no table_id")

        layer0_objects = self.layer0_repo.get_objects(
            table_id=table_meta.table_id,
            limit=10,
            offset=0,
        )

        search_params = {}
        search_types = {}

        for layer0_object in layer0_objects:
            icrs_obj = layer0_object.get(model.ICRSCatalogObject)
            if icrs_obj is not None:
                search_params[layer0_object.object_id] = self.selector.extract_search_params(layer0_object.data)
                search_types[search_params[layer0_object.object_id].name()] = self.selector

        layer2_results = self.layer2_repo.query_batch(
            catalogs=[model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION],
            search_types=search_types,
            search_params=search_params,
            limit=len(layer0_objects) * 10,  # Allow multiple matches per object
            offset=0,
        )

        results: dict[str, model.CIResult] = {}

        for layer0_object in layer0_objects:
            layer2_objects = layer2_results.get(layer0_object.object_id, [])
            probabilities: list[tuple[model.Layer2Object, float]] = []

            for layer2_object in layer2_objects:
                probabilities.append((layer2_object, self.matcher(layer0_object, layer2_object)))

            results[layer0_object.object_id] = self.solver(probabilities)

        print(results)

    def cleanup(self):
        self.pg_storage.disconnect()
