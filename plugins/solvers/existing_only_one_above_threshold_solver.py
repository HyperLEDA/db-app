from typing import final

from app.data import model
from app.domain.unification.crossmatch import CISolver


@final
class ExistingOnlyOneAboveThresholdSolver:
    def __init__(self, threshold: float):
        self.threshold = threshold

    def __call__(self, objects: list[tuple[model.Layer2Object, float]]) -> model.CIResult:
        above_threshold = [obj for obj, prob in objects if prob >= self.threshold]

        if len(above_threshold) == 1:
            return model.CIResultObjectExisting(above_threshold[0].pgc)
        pgcs = {obj.pgc for obj, _ in objects}
        return model.CIResultObjectCollision(pgcs=pgcs)


def existing_only_one_above_threshold_solver(threshold: float) -> CISolver:
    return ExistingOnlyOneAboveThresholdSolver(threshold)


name = "existing_only_one_above_threshold"
plugin = existing_only_one_above_threshold_solver
