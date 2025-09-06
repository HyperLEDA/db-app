from typing import final

from app.data import model
from app.domain.unification.crossmatch import CISolver


@final
class OrSolver:
    def __init__(self, solver1: CISolver, solver2: CISolver):
        self.solver1 = solver1
        self.solver2 = solver2

    def __call__(self, objects: list[tuple[model.Layer2Object, float]]) -> model.CIResult:
        result1 = self.solver1(objects)

        if not isinstance(result1, model.CIResultObjectCollision):
            return result1

        return self.solver2(objects)


def or_solver(solver1: CISolver, solver2: CISolver) -> CISolver:
    return OrSolver(solver1, solver2)


name = "or"
plugin = or_solver
