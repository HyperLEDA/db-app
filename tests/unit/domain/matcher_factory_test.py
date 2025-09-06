import unittest

from app.data.model import layer0, layer2
from app.domain.unification.crossmatch.ci_types import CIMatcher
from app.domain.unification.crossmatch.matcher import create_matcher


class DummyMatcher:
    def __init__(self, value: float):
        self.value = value

    def __call__(self, object1: layer0.Layer0Object, object2: layer2.Layer2Object) -> float:
        return self.value


class DummyNestedMatcher:
    def __init__(self, matcher: CIMatcher, multiplier: float):
        self.matcher = matcher
        self.multiplier = multiplier

    def __call__(self, object1: layer0.Layer0Object, object2: layer2.Layer2Object) -> float:
        return self.matcher(object1, object2) * self.multiplier


def dummy_matcher(value: float) -> CIMatcher:
    return DummyMatcher(value)


def dummy_nested_matcher(matcher: CIMatcher, multiplier: float) -> CIMatcher:
    return DummyNestedMatcher(matcher, multiplier)


def dummy_matcher_with_required_param(required_param: str) -> CIMatcher:
    return DummyMatcher(1.0)


class TestCreateMatcher(unittest.TestCase):
    def test_happy_flat_case(self):
        available_matchers = {
            "dummy": dummy_matcher,
        }
        config = {"type": "dummy", "value": 0.5}

        result = create_matcher(config, available_matchers)

        expected = DummyMatcher(0.5)
        self.assertEqual(result.value, expected.value)

    def test_happy_nested_case(self):
        available_matchers = {
            "dummy": dummy_matcher,
            "nested": dummy_nested_matcher,
        }
        config = {
            "type": "nested",
            "matcher": {"type": "dummy", "value": 0.3},
            "multiplier": 2.0,
        }

        result = create_matcher(config, available_matchers)

        expected = DummyNestedMatcher(DummyMatcher(0.3), 2.0)
        self.assertEqual(result.multiplier, expected.multiplier)
        self.assertEqual(result.matcher.value, expected.matcher.value)

    def test_unknown_matcher_type(self):
        available_matchers = {"dummy": dummy_matcher}
        config = {"type": "unknown", "value": 0.5}

        with self.assertRaises(ValueError) as context:
            create_matcher(config, available_matchers)
        self.assertIn("Unknown matcher type: unknown", str(context.exception))

    def test_missing_type_field(self):
        available_matchers = {"dummy": dummy_matcher}
        config = {"value": 0.5}

        with self.assertRaises(ValueError) as context:
            create_matcher(config, available_matchers)
        self.assertIn("Configuration must contain 'type' field", str(context.exception))

    def test_invalid_payload(self):
        available_matchers = {
            "dummy_with_required": dummy_matcher_with_required_param,
        }
        config = {"type": "dummy_with_required", "wrong_param": "value"}

        with self.assertRaises(TypeError):
            create_matcher(config, available_matchers)

    def test_deeply_nested_configuration(self):
        available_matchers = {
            "dummy": dummy_matcher,
            "nested": dummy_nested_matcher,
        }
        config = {
            "type": "nested",
            "matcher": {
                "type": "nested",
                "matcher": {"type": "dummy", "value": 0.2},
                "multiplier": 1.5,
            },
            "multiplier": 3.0,
        }

        result = create_matcher(config, available_matchers)

        expected = DummyNestedMatcher(DummyNestedMatcher(DummyMatcher(0.2), 1.5), 3.0)
        self.assertEqual(result.multiplier, expected.multiplier)
        self.assertEqual(result.matcher.multiplier, expected.matcher.multiplier)
        self.assertEqual(result.matcher.matcher.value, expected.matcher.matcher.value)
