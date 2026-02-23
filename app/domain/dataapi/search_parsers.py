import abc
import re
from typing import final

import astropy.units as u
from astropy import coordinates as coords

from app.data.repositories import layer2

RADIUS_ARCSEC = 1 * u.Unit("arcsec")

HMS_DMS_PATTERN = re.compile(r"^(\d+h\d+m[\d.]+s)([+-]\d+d\d+m[\d.]+s)$", re.IGNORECASE)
J_COORD_PATTERN = re.compile(r"^J(\d{2})(\d{2})([\d.]+)([+-])(\d{2})(\d{2})([\d.]+)$", re.IGNORECASE)


class SearchParser(abc.ABC):
    @abc.abstractmethod
    def parse(self, query: str) -> tuple[layer2.Filter, layer2.SearchParams] | None:
        pass


@final
class NameSearchParser(SearchParser):
    def parse(self, query: str) -> tuple[layer2.Filter, layer2.SearchParams] | None:
        return (
            layer2.DesignationLikeFilter(),
            layer2.DesignationSearchParams(query.strip()),
        )


@final
class HMSDMSCoordinateParser(SearchParser):
    def parse(self, query: str) -> tuple[layer2.Filter, layer2.SearchParams] | None:
        query = query.strip()
        m = HMS_DMS_PATTERN.match(query)
        if m is None:
            return None
        try:
            ra_str = m.group(1).replace("h", ":").replace("m", ":").replace("s", "")
            dec_str = m.group(2).replace("d", ":").replace("m", ":").replace("s", "")
            sky_coord = coords.SkyCoord(
                ra_str + " " + dec_str,
                unit=(u.Unit("hourangle"), u.Unit("deg")),
            )
        except Exception:
            return None
        return (
            layer2.ICRSCoordinatesInRadiusFilter(RADIUS_ARCSEC),
            layer2.ICRSSearchParams(coords=sky_coord),
        )


def _parse_j_coord_to_skycoord(query: str) -> coords.SkyCoord:
    m = J_COORD_PATTERN.match(query.strip())
    if m is None:
        raise ValueError("Does not match J coordinate format")
    ra_h, ra_m, ra_s, dec_sign, dec_d, dec_m, dec_s = m.groups()
    ra_str = f"{ra_h}:{ra_m}:{ra_s}"
    dec_str = f"{dec_sign}{dec_d}:{dec_m}:{dec_s}"
    return coords.SkyCoord(
        ra_str + " " + dec_str,
        unit=(u.Unit("hourangle"), u.Unit("deg")),
    )


@final
class JCoordinateParser(SearchParser):
    def parse(self, query: str) -> tuple[layer2.Filter, layer2.SearchParams] | None:
        query = query.strip()
        if not query.upper().startswith("J"):
            return None
        try:
            sky_coord = _parse_j_coord_to_skycoord(query)
        except (ValueError, Exception):
            return None
        return (
            layer2.ICRSCoordinatesInRadiusFilter(RADIUS_ARCSEC),
            layer2.ICRSSearchParams(coords=sky_coord),
        )


DEFAULT_PARSERS: list[SearchParser] = [
    NameSearchParser(),
    HMSDMSCoordinateParser(),
    JCoordinateParser(),
]


def query_to_filters(
    query: str,
    parsers: list[SearchParser],
) -> tuple[layer2.Filter, layer2.SearchParams]:
    results: list[tuple[layer2.Filter, layer2.SearchParams]] = []
    for parser in parsers:
        parsed = parser.parse(query)
        if parsed is not None:
            results.append(parsed)
    if not results:
        return (
            layer2.DesignationLikeFilter(),
            layer2.DesignationSearchParams(query.strip()),
        )
    if len(results) == 1:
        return results[0]
    filters = [f for f, _ in results]
    params = [p for _, p in results]
    return layer2.OrFilter(filters), layer2.CombinedSearchParams(params)
