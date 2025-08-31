from typing import final

from app.data import model
from app.domain.unification.crossmatch import CISolver


@final
class NewAllBelowThresholdSolver:
    def __init__(self, threshold: float):
        self.threshold = threshold

    def __call__(self, objects: list[tuple[model.Layer2Object, float]]) -> model.CIResult:
        all_below = all(prob < self.threshold for _, prob in objects)

        if all_below:
            return model.CIResultObjectNew()
        pgcs = {obj.pgc for obj, _ in objects}
        return model.CIResultObjectCollision(pgcs=pgcs)


def new_all_below_threshold_solver(threshold: float) -> CISolver:
    return NewAllBelowThresholdSolver(threshold)


name = "new_all_below_threshold"
plugin = new_all_below_threshold_solver
