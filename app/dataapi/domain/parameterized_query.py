from astropy import coordinates as coords

from app import catalogs
from app.dataapi import repository, responders
from app.dataapi.domain import reddening
from app.lib import astronomy
from app.lib.web.errors import RuleValidationError
from app.specs import dataapi as spec

CATALOGS_FOR_PGC_QUERY = [
    catalogs.RawCatalog.DESIGNATION,
    catalogs.RawCatalog.ADDITIONAL_DESIGNATIONS,
    catalogs.RawCatalog.ICRS,
    catalogs.RawCatalog.REDSHIFT,
    catalogs.RawCatalog.NATURE,
    catalogs.RawCatalog.NOTE,
    catalogs.RawCatalog.PHOTOMETRY__TOTAL,
]


def resolve_query_catalogs(
    catalog_names: list[str] | None,
    default_catalogs: list[catalogs.RawCatalog],
) -> list[catalogs.RawCatalog]:
    if catalog_names is None:
        return default_catalogs
    if not catalog_names:
        raise RuleValidationError("catalogs must not be empty")

    allowed = set(default_catalogs)
    result: list[catalogs.RawCatalog] = []
    seen: set[catalogs.RawCatalog] = set()
    for name in catalog_names:
        try:
            catalog = catalogs.RawCatalog(name)
        except ValueError as exc:
            valid = ", ".join(c.value for c in catalogs.RawCatalog)
            raise RuleValidationError(f"Unknown catalog {name!r}; valid values are: {valid}") from exc
        if catalog not in allowed:
            allowed_names = ", ".join(c.value for c in default_catalogs)
            raise RuleValidationError(f"Catalog {name!r} is not available for this query; available: {allowed_names}")
        if catalog not in seen:
            seen.add(catalog)
            result.append(catalog)
    return result


def _resolve_pgcs(
    repo: repository.Repository,
    query: spec.QuerySimpleRequest,
    limit: int,
    offset: int,
) -> list[int]:
    if query.pgcs is not None:
        return sorted(query.pgcs)[offset : offset + limit]

    if query.name is not None:
        return repo.find_pgcs_by_designation(query.name, limit, offset)

    if query.ra is not None and query.dec is not None:
        if query.radius is not None:
            return _find_pgcs_by_equatorial(repo, query.ra, query.dec, query.radius, query.eq_epoch, limit, offset)
        return repo.find_pgcs_unfiltered(limit, offset)

    if query.glon is not None and query.glat is not None:
        if query.radius is not None:
            return _find_pgcs_by_galactic(repo, query.glon, query.glat, query.radius, limit, offset)
        return repo.find_pgcs_unfiltered(limit, offset)

    if query.sgl is not None and query.sgb is not None:
        if query.radius is not None:
            return _find_pgcs_by_supergalactic(repo, query.sgl, query.sgb, query.radius, limit, offset)
        return repo.find_pgcs_unfiltered(limit, offset)

    return repo.find_pgcs_unfiltered(limit, offset)


def _find_pgcs_by_equatorial(
    repo: repository.Repository,
    ra: object,
    dec: object,
    radius: object,
    eq_epoch: str,
    limit: int,
    offset: int,
) -> list[int]:
    equinox = astronomy.parse_coordinate_epoch(eq_epoch)
    coord = coords.SkyCoord(ra=ra, dec=dec, frame=coords.FK5(equinox=equinox))
    icrs = coord.transform_to("icrs")
    return repo.find_pgcs_by_equatorial(
        float(icrs.ra.deg),
        float(icrs.dec.deg),
        radius,
        limit,
        offset,
    )


def _find_pgcs_by_galactic(
    repo: repository.Repository,
    glon: object,
    glat: object,
    radius: object,
    limit: int,
    offset: int,
) -> list[int]:
    icrs = coords.SkyCoord(l=glon, b=glat, frame="galactic").transform_to("icrs")
    return repo.find_pgcs_by_equatorial(
        float(icrs.ra.deg),
        float(icrs.dec.deg),
        radius,
        limit,
        offset,
    )


def _find_pgcs_by_supergalactic(
    repo: repository.Repository,
    sgl: object,
    sgb: object,
    radius: object,
    limit: int,
    offset: int,
) -> list[int]:
    icrs = coords.SkyCoord(sgl=sgl, sgb=sgb, frame="supergalactic").transform_to("icrs")
    return repo.find_pgcs_by_equatorial(
        float(icrs.ra.deg),
        float(icrs.dec.deg),
        radius,
        limit,
        offset,
    )


class ParameterizedQueryManager:
    def __init__(
        self,
        repo: repository.Repository,
        enabled_catalogs: list[catalogs.RawCatalog],
        catalog_cfg: responders.CatalogConfig,
        reddening_service: reddening.Reddening,
    ) -> None:
        self.repo = repo
        self.enabled_catalogs = enabled_catalogs
        self.catalog_config = catalog_cfg
        self.reddening_service = reddening_service

    def query_simple(self, query: spec.QuerySimpleRequest) -> spec.QuerySimpleResponse:
        responder = responders.StructuredResponder(self.catalog_config, self.reddening_service)
        offset = query.page * query.page_size

        default_catalogs = CATALOGS_FOR_PGC_QUERY if query.pgcs is not None else self.enabled_catalogs
        raw_catalogs = resolve_query_catalogs(query.catalogs, default_catalogs)

        pgcs = _resolve_pgcs(self.repo, query, query.page_size, offset)
        objects = self.repo.query_catalogs(raw_catalogs, pgcs)
        return responder.build_response(objects)
