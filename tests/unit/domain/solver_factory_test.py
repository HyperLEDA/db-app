import unittest

from app.data import model
from app.domain.unification.crossmatch.ci_types import CISolver
from app.domain.unification.crossmatch.solver import create_solver


class DummySolver:
    def __init__(self, threshold: float):
        self.threshold = threshold

    def __call__(self, objects: list[tuple[model.Layer2Object, float]]) -> model.CIResult:
        return model.CIResultObjectNew()


class DummyNestedSolver:
    def __init__(self, solver1: CISolver, solver2: CISolver):
        self.solver1 = solver1
        self.solver2 = solver2

    def __call__(self, objects: list[tuple[model.Layer2Object, float]]) -> model.CIResult:
        return self.solver1(objects)


def dummy_solver(threshold: float) -> CISolver:
    return DummySolver(threshold)


def dummy_nested_solver(solver1: CISolver, solver2: CISolver) -> CISolver:
    return DummyNestedSolver(solver1, solver2)


def dummy_solver_with_required_param(required_param: str) -> CISolver:
    return DummySolver(1.0)


class TestCreateSolver(unittest.TestCase):
    def test_happy_flat_case(self):
        available_solvers = {
            "dummy": dummy_solver,
        }
        config = {"type": "dummy", "threshold": 0.5}

        result = create_solver(config, available_solvers)

        expected = DummySolver(0.5)
        self.assertEqual(result.threshold, expected.threshold)

    def test_happy_nested_case(self):
        available_solvers = {
            "dummy": dummy_solver,
            "nested": dummy_nested_solver,
        }
        config = {
            "type": "nested",
            "solver1": {"type": "dummy", "threshold": 0.3},
            "solver2": {"type": "dummy", "threshold": 0.7},
        }

        result = create_solver(config, available_solvers)

        expected = DummyNestedSolver(DummySolver(0.3), DummySolver(0.7))
        self.assertEqual(result.solver1.threshold, expected.solver1.threshold)
        self.assertEqual(result.solver2.threshold, expected.solver2.threshold)

    def test_unknown_solver_type(self):
        available_solvers = {"dummy": dummy_solver}
        config = {"type": "unknown", "threshold": 0.5}

        with self.assertRaises(ValueError) as context:
            create_solver(config, available_solvers)
        self.assertIn("Unknown solver type: unknown", str(context.exception))

    def test_missing_type_field(self):
        available_solvers = {"dummy": dummy_solver}
        config = {"threshold": 0.5}

        with self.assertRaises(ValueError) as context:
            create_solver(config, available_solvers)
        self.assertIn("Configuration must contain 'type' field", str(context.exception))

    def test_invalid_payload(self):
        available_solvers = {
            "dummy_with_required": dummy_solver_with_required_param,
        }
        config = {"type": "dummy_with_required", "wrong_param": "value"}

        with self.assertRaises(TypeError):
            create_solver(config, available_solvers)
