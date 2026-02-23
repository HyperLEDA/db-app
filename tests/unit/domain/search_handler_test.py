import unittest

from app.data.repositories import layer2
from app.domain.dataapi.search_parsers import (
    DEFAULT_PARSERS,
    query_to_filters,
)


class TestQueryToFiltersPipeline(unittest.TestCase):
    def test_plain_name_produces_designation_like_only(self):
        filters, search_params = query_to_filters("M33", DEFAULT_PARSERS)
        assert isinstance(filters, layer2.DesignationLikeFilter)
        assert isinstance(search_params, layer2.DesignationSearchParams)
        assert search_params.get_params()["design"] == "M33"

    def test_j_coord_produces_or_filter_with_name_and_coords(self):
        filters, search_params = query_to_filters("J123049.32+122233.2", DEFAULT_PARSERS)
        assert isinstance(filters, layer2.OrFilter)
        assert isinstance(search_params, layer2.CombinedSearchParams)
        params = search_params.get_params()
        assert "design" in params
        assert "ra" in params
        assert "dec" in params
        assert " OR " in filters.get_query()

    def test_hms_dms_coord_produces_or_filter_with_name_and_coords(self):
        filters, search_params = query_to_filters("12h30m49.32s+12d22m33.2s", DEFAULT_PARSERS)
        assert isinstance(filters, layer2.OrFilter)
        assert isinstance(search_params, layer2.CombinedSearchParams)
        params = search_params.get_params()
        assert "design" in params
        assert "ra" in params
        assert "dec" in params
        assert " OR " in filters.get_query()

    def test_non_coord_string_produces_only_designation_like(self):
        filters, search_params = query_to_filters("some random object name", DEFAULT_PARSERS)
        assert isinstance(filters, layer2.DesignationLikeFilter)
        assert isinstance(search_params, layer2.DesignationSearchParams)
        assert search_params.get_params()["design"] == "some random object name"
