from typing import final

import astropy.units as u
from astropy import coordinates as coords

from app.data import model, repositories
from app.data.repositories import layer2
from app.domain import expressions, responders
from app.domain.dataapi import parameterized_query
from app.presentation import dataapi

ENABLED_CATALOGS = [
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.ICRS,
    model.RawCatalog.REDSHIFT,
]


@final
class Actions(dataapi.Actions):
    def __init__(self, layer2_repo: repositories.Layer2Repository) -> None:
        self.layer2_repo = layer2_repo
        self.parameterized_query_manager = parameterized_query.ParameterizedQueryManager(layer2_repo, ENABLED_CATALOGS)

    def query(self, query: dataapi.QueryRequest) -> dataapi.QueryResponse:
        expression = expressions.parse_expression(query.q)
        filters, search_params = expression_to_filter(expression)

        objects = self.layer2_repo.query(
            ENABLED_CATALOGS,
            filters,
            search_params,
            query.page_size,
            query.page,
        )

        responder = responders.JSONResponder()
        pgc_objects = responder.build_response(objects)
        return dataapi.QueryResponse(objects=pgc_objects)

    def query_fits(self, query: dataapi.FITSRequest) -> bytes:
        return self.parameterized_query_manager.query_fits(query)

    def query_simple(self, query: dataapi.QuerySimpleRequest) -> dataapi.QuerySimpleResponse:
        return self.parameterized_query_manager.query_simple(query)


def parse_coordinates(coord_str: str) -> coords.SkyCoord:
    try:
        if coord_str.startswith(("J", "B")):
            return coords.SkyCoord(coord_str[1:], unit=(u.hourangle, u.deg))

        if coord_str.startswith("G"):
            long, lat = map(float, coord_str[1:].split("+"))
            coord = coords.SkyCoord(l=long * u.deg, b=lat * u.deg, frame="galactic")
            return coord.transform_to("icrs")

        return coords.SkyCoord(coord_str, unit=(u.hourangle, u.deg))
    except Exception as e:
        raise ValueError(f"Invalid coordinate format: {coord_str}") from e


def parse_function_node(node: expressions.FunctionNode) -> tuple[layer2.Filter, layer2.SearchParams]:
    if node.function == expressions.FunctionName.PGC:
        try:
            pgc = int(node.value)
        except ValueError as e:
            raise ValueError(f"Invalid PGC value: '{node.value}'") from e

        return layer2.PGCOneOfFilter([pgc]), layer2.CombinedSearchParams([])
    if node.function == expressions.FunctionName.NAME:
        return layer2.DesignationCloseFilter(2), layer2.DesignationSearchParams(node.value)
    if node.function == expressions.FunctionName.POS:
        return layer2.ICRSCoordinatesInRadiusFilter(1 * u.arcsec), layer2.ICRSSearchParams(
            coords=parse_coordinates(node.value)
        )

    raise ValueError(f"Unsupported function: {node.function}")


def expression_to_filter(expr: expressions.Node) -> tuple[layer2.Filter, layer2.SearchParams]:
    if isinstance(expr, expressions.AndNode):
        left_filter, left_search_params = expression_to_filter(expr.left)
        right_filter, right_search_params = expression_to_filter(expr.right)

        return layer2.AndFilter([left_filter, right_filter]), layer2.CombinedSearchParams(
            [left_search_params, right_search_params]
        )
    if isinstance(expr, expressions.OrNode):
        left_filter, left_search_params = expression_to_filter(expr.left)
        right_filter, right_search_params = expression_to_filter(expr.right)

        return layer2.OrFilter([left_filter, right_filter]), layer2.CombinedSearchParams(
            [left_search_params, right_search_params]
        )

    return parse_function_node(expr)

    return None
