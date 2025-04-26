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

    def query_simple(self, query: dataapi.QuerySimpleRequest) -> dataapi.QuerySimpleResponse:
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

        objects = self.layer2_repo.query(
            ENABLED_CATALOGS,
            layer2.AndFilter(filters),
            layer2.CombinedSearchParams(search_params),
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

        # Query all objects without pagination
        objects = self.layer2_repo.query(
            ENABLED_CATALOGS,
            layer2.AndFilter(filters),
            layer2.CombinedSearchParams(search_params),
            1000000,  # Large number instead of None
            0,  # First page
        )

        # Extract data from Layer2Objects
        pgcs = []
        ras = []
        decs = []
        czs = []
        names = []

        for obj in objects:
            pgcs.append(obj.pgc)

            # Find ICRS data
            icrs_data = next((c for c in obj.data if isinstance(c, model.ICRSCatalogObject)), None)
            if icrs_data:
                ras.append(icrs_data.ra)
                decs.append(icrs_data.dec)
            else:
                ras.append(0.0)
                decs.append(0.0)

            # Find redshift data
            redshift_data = next((c for c in obj.data if isinstance(c, model.RedshiftCatalogObject)), None)
            if redshift_data:
                czs.append(redshift_data.cz)
            else:
                czs.append(0.0)

            # Find designation data
            designation_data = next((c for c in obj.data if isinstance(c, model.DesignationCatalogObject)), None)
            if designation_data:
                names.append(designation_data.designation)
            else:
                names.append("")

        pgcs_array = np.array(pgcs, dtype=np.int32)
        ras_array = np.array(ras, dtype=np.float64)
        decs_array = np.array(decs, dtype=np.float64)
        czs_array = np.array(czs, dtype=np.float64)
        names_array = np.array(names, dtype="S32")

        hdu = fits.BinTableHDU.from_columns(
            [
                fits.Column(name="PGC", format="J", array=pgcs_array),
                fits.Column(name="RA", format="D", array=ras_array),
                fits.Column(name="DEC", format="D", array=decs_array),
                fits.Column(name="REDSHIFT", format="D", array=czs_array),
                fits.Column(name="NAME", format="A32", array=names_array),
            ]
        )

        # Create primary HDU with metadata
        primary_hdu = fits.PrimaryHDU()
        primary_hdu.header["QUERY_RA"] = query.ra if query.ra is not None else 0.0
        primary_hdu.header["QUERY_DEC"] = query.dec if query.dec is not None else 0.0
        primary_hdu.header["QUERY_RAD"] = query.radius if query.radius is not None else 0.0
        primary_hdu.header["QUERY_NAME"] = query.name if query.name is not None else ""
        primary_hdu.header["QUERY_CZ"] = query.cz if query.cz is not None else 0.0
        primary_hdu.header["QUERY_CZERR"] = query.cz_err_percent if query.cz_err_percent is not None else 0.0

        # Create HDU list and write to bytes
        hdul = fits.HDUList([primary_hdu, hdu])
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
