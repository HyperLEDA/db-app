from typing import final

import structlog

from app.domain.unification import crossmatch
from app.tasks import interface
from plugins.loader import discover_matchers, discover_solvers

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
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name
        self.log = structlog.get_logger()

    @classmethod
    def name(cls) -> str:
        return "crossmatch"

    def prepare(self, config: interface.Config):
        self.log.info("Preparing crossmatch task", table_name=self.table_name)

        self.log.info("Loading cross-identification plugins")
        matchers = discover_matchers("plugins/matchers")
        solvers = discover_solvers("plugins/solvers")

        matcher = crossmatch.create_matcher(test_matcher_config, matchers)
        solver = crossmatch.create_solver(test_solver_config, solvers)
        print(matcher, solver)

        self.log.info("matchers", lst=matchers.keys())
        self.log.info("solvers", lst=solvers.keys())

    def run(self):
        self.log.info("Running crossmatch task", table_name=self.table_name)
        # Dummy implementation - just log and exit successfully

    def cleanup(self):
        self.log.info("Cleaning up crossmatch task", table_name=self.table_name)
