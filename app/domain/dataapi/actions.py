import io

import astropy.units as u
import numpy as np
from astropy import coordinates as coords
from astropy.io import fits

from app.data import model, repositories
from app.data.repositories import layer2
from app.domain import expressions
from app.presentation import dataapi

ENABLED_CATALOGS = [
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.ICRS,
    model.RawCatalog.REDSHIFT,
]


class Actions(dataapi.Actions):
    def __init__(self, layer2_repo: repositories.Layer2Repository) -> None:
        self.layer2_repo = layer2_repo

    def _build_filters_and_params(
        self, query: dataapi.QuerySimpleRequest | dataapi.FITSRequest
    ) -> tuple[layer2.Filter, layer2.SearchParams]:
        filters = []
        search_params = []

        if query.pgcs is not None:
            filters.append(layer2.PGCOneOfFilter(query.pgcs))

        if (query.ra is not None) and (query.dec is not None) and (query.radius is not None):
            filters.append(layer2.ICRSCoordinatesInRadiusFilter(query.radius))
            search_params.append(layer2.ICRSSearchParams(query.ra, query.dec))

        if query.name is not None:
            filters.append(layer2.DesignationCloseFilter(3))
            search_params.append(layer2.DesignationSearchParams(query.name))

        if (query.cz is not None) and (query.cz_err_percent is not None):
            filters.append(layer2.RedshiftCloseFilter(query.cz, query.cz_err_percent))

        return layer2.AndFilter(filters), layer2.CombinedSearchParams(search_params)

    def _extract_object_data(self, objects: list[model.Layer2Object]) -> dict[str, np.ndarray]:
        data_dict = {}

        for obj in objects:
            if "PGC" not in data_dict:
                data_dict["PGC"] = []

            for catalog_obj in obj.data:
                catalog_name = catalog_obj.catalog().value
                catalog_data = catalog_obj.layer2_data()

                if isinstance(catalog_data, dict):
                    for field, _ in catalog_data.items():
                        full_field_name = f"{catalog_name}_{field}"
                        if full_field_name not in data_dict:
                            data_dict[full_field_name] = []
                else:
                    if catalog_name not in data_dict:
                        data_dict[catalog_name] = []

        for obj in objects:
            for field in data_dict:
                data_dict[field].append(None)

            data_dict["PGC"][-1] = obj.pgc

            for catalog_obj in obj.data:
                catalog_name = catalog_obj.catalog().value
                catalog_data = catalog_obj.layer2_data()

                if isinstance(catalog_data, dict):
                    for field, value in catalog_data.items():
                        full_field_name = f"{catalog_name}_{field}"
                        data_dict[full_field_name][-1] = value
                else:
                    data_dict[catalog_name][-1] = catalog_data

        for field, values in data_dict.items():
            if all(v is None for v in values):
                data_dict[field] = np.array([], dtype=np.float64)
            else:
                if all(isinstance(v, int | type(None)) for v in values):
                    data_dict[field] = np.array(values, dtype=np.int32)
                elif all(isinstance(v, float | type(None)) for v in values):
                    data_dict[field] = np.array(values, dtype=np.float64)
                elif all(isinstance(v, str | type(None)) for v in values):
                    max_len = max(len(str(v)) for v in values if v is not None)
                    data_dict[field] = np.array(values, dtype=f"S{max_len}")
                else:
                    data_dict[field] = np.array(values, dtype=object)

        return data_dict

    def _create_fits_hdul(self, query: dataapi.FITSRequest, objects: list[model.Layer2Object]) -> fits.HDUList:
        data_dict = self._extract_object_data(objects)

        columns = []
        for field, array in data_dict.items():
            if len(array) == 0:
                continue

            if array.dtype.kind == "i":
                fits_format = "J"
            elif array.dtype.kind == "f":
                fits_format = "D"
            elif array.dtype.kind == "S":
                fits_format = f"A{array.dtype.itemsize}"
            else:
                fits_format = "A32"

            columns.append(fits.Column(name=field, format=fits_format, array=array))

        hdu = fits.BinTableHDU.from_columns(columns)

        primary_hdu = fits.PrimaryHDU()
        for param, value in vars(query).items():
            if value is not None:
                primary_hdu.header[f"QUERY_{param.upper()}"] = value

        return fits.HDUList([primary_hdu, hdu])

    def query_simple(self, query: dataapi.QuerySimpleRequest) -> dataapi.QuerySimpleResponse:
        filters, search_params = self._build_filters_and_params(query)

        objects = self.layer2_repo.query(
            ENABLED_CATALOGS,
            filters,
            search_params,
            query.page_size,
            query.page,
        )

        return dataapi.QuerySimpleResponse(objects_to_response(objects))

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

        return dataapi.QueryResponse(objects_to_response(objects))

    def query_fits(self, query: dataapi.FITSRequest) -> bytes:
        filters, search_params = self._build_filters_and_params(query)

        objects = self.layer2_repo.query(
            ENABLED_CATALOGS,
            filters,
            search_params,
            query.page_size,
            query.page,
        )

        hdul = self._create_fits_hdul(query, objects)

        with io.BytesIO() as f:
            hdul.writeto(f)
            return f.getvalue()


def objects_to_response(objects: list[model.Layer2Object]) -> list[dataapi.PGCObject]:
    response_objects = []
    for obj in objects:
        catalog_data = {o.catalog().value: o.layer2_data() for o in obj.data}
        response_objects.append(dataapi.PGCObject(obj.pgc, catalog_data))

    return response_objects


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
