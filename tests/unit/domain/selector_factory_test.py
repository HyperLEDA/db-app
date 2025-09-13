import unittest
from typing import Any, cast, final

from app.data.model.interface import CatalogObject
from app.data.repositories.layer2 import Filter
from app.data.repositories.layer2.params import SearchParams
from app.domain.unification.crossmatch import create_selector


@final
class DummyFilter(Filter):
    def __init__(self, value: str):
        self.value = value

    def get_query(self) -> str:
        return "dummy = %s"

    def get_params(self) -> list[Any]:
        return [self.value]

    def extract_search_params(self, object_info: list[CatalogObject]) -> SearchParams:
        raise NotImplementedError


@final
class DummyNestedFilter(Filter):
    def __init__(self, filter1: Filter, filter2: Filter):
        self.filter1 = filter1
        self.filter2 = filter2

    def get_query(self) -> str:
        return f"({self.filter1.get_query()}) AND ({self.filter2.get_query()})"

    def get_params(self) -> list[Any]:
        params = []
        params.extend(self.filter1.get_params())
        params.extend(self.filter2.get_params())
        return params

    def extract_search_params(self, object_info: list[CatalogObject]) -> SearchParams:
        raise NotImplementedError


@final
class DummyListFilter(Filter):
    def __init__(self, filters: list[Filter]):
        self.filters = filters

    def get_query(self) -> str:
        queries = [f.get_query() for f in self.filters]
        return " OR ".join([f"({q})" for q in queries]) or "1=1"

    def get_params(self) -> list[Any]:
        params = []
        for f in self.filters:
            params.extend(f.get_params())
        return params

    def extract_search_params(self, object_info: list[CatalogObject]) -> SearchParams:
        raise NotImplementedError


@final
class DummyFilterWithRequiredParam(Filter):
    def __init__(self, required_param: str):
        self.required_param = required_param

    def get_query(self) -> str:
        return "required = %s"

    def get_params(self) -> list[Any]:
        return [self.required_param]

    def extract_search_params(self, object_info: list[CatalogObject]) -> SearchParams:
        raise NotImplementedError


class TestCreateSelector(unittest.TestCase):
    def test_flat_happy_case(self):
        available_filters = {
            "dummy": DummyFilter,
        }
        config = {"type": "dummy", "value": "test_value"}

        result = create_selector(config, available_filters)

        self.assertIsInstance(result, DummyFilter)
        dummy_result = cast(DummyFilter, result)
        self.assertEqual(dummy_result.value, "test_value")
        self.assertEqual(dummy_result.get_query(), "dummy = %s")
        self.assertEqual(dummy_result.get_params(), ["test_value"])

    def test_nested_happy_case(self):
        available_filters = {
            "dummy": DummyFilter,
            "nested": DummyNestedFilter,
        }
        config = {
            "type": "nested",
            "filter1": {"type": "dummy", "value": "value1"},
            "filter2": {"type": "dummy", "value": "value2"},
        }

        result = create_selector(config, available_filters)

        self.assertIsInstance(result, DummyNestedFilter)
        nested_result = cast(DummyNestedFilter, result)
        self.assertIsInstance(nested_result.filter1, DummyFilter)
        self.assertIsInstance(nested_result.filter2, DummyFilter)
        self.assertEqual(cast(DummyFilter, nested_result.filter1).value, "value1")
        self.assertEqual(cast(DummyFilter, nested_result.filter2).value, "value2")

    def test_nested_list_case(self):
        available_filters = {
            "dummy": DummyFilter,
            "list_filter": DummyListFilter,
        }
        config = {
            "type": "list_filter",
            "filters": [
                {"type": "dummy", "value": "value1"},
                {"type": "dummy", "value": "value2"},
            ],
        }

        result = create_selector(config, available_filters)

        self.assertIsInstance(result, DummyListFilter)
        list_result = cast(DummyListFilter, result)
        self.assertEqual(len(list_result.filters), 2)
        self.assertIsInstance(list_result.filters[0], DummyFilter)
        self.assertIsInstance(list_result.filters[1], DummyFilter)
        self.assertEqual(cast(DummyFilter, list_result.filters[0]).value, "value1")
        self.assertEqual(cast(DummyFilter, list_result.filters[1]).value, "value2")

    def test_unknown_filter(self):
        available_filters = {"dummy": DummyFilter}
        config = {"type": "unknown", "value": "test_value"}

        with self.assertRaises(ValueError) as context:
            create_selector(config, available_filters)
        self.assertIn("Unknown filter type: unknown", str(context.exception))

    def test_missing_type_field(self):
        available_filters = {"dummy": DummyFilter}
        config = {"value": "test_value"}

        with self.assertRaises(ValueError) as context:
            create_selector(config, available_filters)
        self.assertIn("Configuration must contain 'type' field", str(context.exception))

    def test_known_filter_with_unexpected_arguments(self):
        available_filters = {
            "dummy_with_required": DummyFilterWithRequiredParam,
        }
        config = {"type": "dummy_with_required", "wrong_param": "value"}

        with self.assertRaises(TypeError):
            create_selector(config, available_filters)

    def test_empty_list_handling(self):
        available_filters = {
            "dummy": DummyFilter,
            "list_filter": DummyListFilter,
        }
        config = {
            "type": "list_filter",
            "filters": [],
        }

        result = create_selector(config, available_filters)

        self.assertIsInstance(result, DummyListFilter)
        list_result = cast(DummyListFilter, result)
        self.assertEqual(len(list_result.filters), 0)

    def test_mixed_list_with_dicts_raises_error(self):
        available_filters = {
            "dummy": DummyFilter,
        }
        config = {
            "type": "dummy",
            "value": "test_value",
            "mixed_list": [{"type": "dummy", "value": "nested"}, "simple_string"],
        }

        with self.assertRaises(ValueError) as context:
            create_selector(config, available_filters)
        self.assertIn("Configuration must contain 'type' field", str(context.exception))
