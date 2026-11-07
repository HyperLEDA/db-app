from typing import Any, override

import structlog
from astropy import units as u

from app.catalogs import layer2
from app.dataapi import model
from app.dataapi.domain import reddening
from app.dataapi.responders import interface
from app.lib import astronomy
from app.lib.web import errors
from app.specs import dataapi as spec

logger = structlog.stdlib.get_logger()

DATA_SCHEMA = spec.Schema(
    units=spec.Units(
        coordinates=spec.CoordinateUnits(
            equatorial=spec.EquatorialCoordinatesUnits(
                ra="deg",
                dec="deg",
                e_ra="arcsec",
                e_dec="arcsec",
            ),
            galactic=spec.GalacticCoordinatesUnits(
                lon="deg",
                lat="deg",
                e_lon="arcsec",
                e_lat="arcsec",
            ),
            supergalactic=spec.SupergalacticCoordinatesUnits(
                lon="deg",
                lat="deg",
                e_lon="arcsec",
                e_lat="arcsec",
            ),
        ),
        velocity={},
    )
)

VELOCITY_SCHEMA = spec.AbsoluteVelocityUnits(
    v="km/s",
    e_v="km/s",
)


def _coordinates_from_icrs(ra: float, dec: float, e_ra: float, e_dec: float) -> spec.Coordinates:
    eq_e_ra = astronomy.to(e_ra * u.Unit("deg"), "arcsec")
    eq_e_dec = astronomy.to(e_dec * u.Unit("deg"), "arcsec")
    lon, lat, e_lon, e_lat = astronomy.equatorial_to_lonlat(ra, dec, e_ra, e_dec, "galactic")
    sg_lon, sg_lat, sg_e_lon, sg_e_lat = astronomy.equatorial_to_lonlat(ra, dec, e_ra, e_dec, "supergalactic")
    return spec.Coordinates(
        equatorial=spec.EquatorialCoordinates(ra=ra, dec=dec, e_ra=eq_e_ra, e_dec=eq_e_dec),
        galactic=spec.GalacticCoordinates(lon=lon, lat=lat, e_lon=e_lon, e_lat=e_lat),
        supergalactic=spec.SupergalacticCoordinates(lon=sg_lon, lat=sg_lat, e_lon=sg_e_lon, e_lat=sg_e_lat),
    )


def _redshift_from_cz(cz: float, e_cz: float) -> spec.Redshift:
    return spec.Redshift(
        z=astronomy.heliocentric_cz_to_z(cz * u.Unit("km/s")),
        e_z=astronomy.heliocentric_cz_to_z(e_cz * u.Unit("km/s")),
    )


def _photometry_total_measurement(measurement: model.PhotometryTotalMeasurement) -> spec.PhotometryTotalMeasurement:
    return spec.PhotometryTotalMeasurement(
        band=measurement.band,
        magsys=measurement.magsys,
        method=measurement.method,
        wavelength=measurement.wavelength,
        mag=measurement.mag,
        e_mag=measurement.e_mag,
    )


def _velocities_from_stored(
    velocities: dict[str, model.Velocity],
    catalog_schema: spec.Schema,
) -> dict[str, spec.AbsoluteVelocity]:
    result: dict[str, spec.AbsoluteVelocity] = {}
    for key, measurement in velocities.items():
        catalog_schema.units.velocity[key] = VELOCITY_SCHEMA
        result[key] = spec.AbsoluteVelocity(v=measurement.v, e_v=measurement.e_v)
    return result


class StructuredResponder(interface.ObjectResponder):
    def __init__(self, reddening_service: reddening.Reddening) -> None:
        self.reddening_service = reddening_service

    def _fetch_corrected_photometry(
        self,
        objects: list[model.Layer2Object],
    ) -> dict[int, list[spec.PhotometryTotalMeasurement]]:
        correction_work: list[tuple[int, model.ICRSCatalog, list[model.PhotometryTotalMeasurement]]] = []
        for obj in objects:
            if obj.catalogs.photometry_total is None or obj.catalogs.icrs is None:
                continue
            correction_work.append((obj.pgc, obj.catalogs.icrs, obj.catalogs.photometry_total.measurements))

        query_list: list[reddening.ReddeningQuery] = []
        query_key_to_index: dict[tuple[str, float, float], int] = {}
        for _, icrs, measurements in correction_work:
            coordinate = spec.J2000Coordinate(ra=icrs.ra, dec=icrs.dec)
            for photsys in {measurement.photsys for measurement in measurements}:
                key = (photsys, icrs.ra, icrs.dec)
                if key not in query_key_to_index:
                    query_key_to_index[key] = len(query_list)
                    query_list.append(reddening.ReddeningQuery(photsys=photsys, coordinate=coordinate))

        if not query_list:
            return {}

        try:
            results = self.reddening_service.calculate(query_list)
        except errors.InternalError as exc:
            logger.warning(
                "Field API unavailable, skipping photometry extinction correction",
                error=str(exc),
            )
            return {}
        extinction_lookup: dict[tuple[str, float, float, str], float] = {}
        for query_index, query in enumerate(query_list):
            ra = query.coordinate.ra
            dec = query.coordinate.dec
            for filter_value in results[query_index].filters:
                extinction_lookup[(query.photsys, ra, dec, filter_value.filter)] = filter_value.a

        corrected_by_pgc: dict[int, list[spec.PhotometryTotalMeasurement]] = {}
        for pgc, icrs, measurements in correction_work:
            corrected: list[spec.PhotometryTotalMeasurement] = []
            for measurement in measurements:
                extinction = extinction_lookup.get((measurement.photsys, icrs.ra, icrs.dec, measurement.filter))
                if extinction is None:
                    continue
                corrected.append(
                    spec.PhotometryTotalMeasurement(
                        band=measurement.band,
                        magsys=measurement.magsys,
                        method=measurement.method,
                        wavelength=measurement.wavelength,
                        mag=measurement.mag - extinction,
                        e_mag=measurement.e_mag,
                    )
                )
            if corrected:
                corrected_by_pgc[pgc] = corrected
        return corrected_by_pgc

    @override
    def build_response_from_catalog(self, objects: list[layer2.Layer2Object]) -> Any:
        catalog_schema = DATA_SCHEMA
        pgc_objects = []

        for obj in objects:
            result = spec.Catalogs()

            if (designation := obj.get(layer2.DesignationCatalogObject)) is not None:
                result.designation = spec.Designation(name=designation.designation)

            icrs = obj.get(layer2.ICRSCatalogObject)
            if icrs is not None:
                result.coordinates = _coordinates_from_icrs(icrs.ra, icrs.dec, icrs.e_ra, icrs.e_dec)

            redshift = obj.get(layer2.RedshiftCatalogObject)
            if redshift is not None:
                result.redshift = _redshift_from_cz(redshift.cz, redshift.e_cz)

            if (nature := obj.get(layer2.NatureCatalogObject)) is not None:
                result.nature = spec.Nature(type_name=nature.type_name)

            if (morphology := obj.get(layer2.MorphologyCatalogObject)) is not None:
                result.morphology = spec.Morphology(t=morphology.t, em=morphology.em, ep=morphology.ep)

            pgc_objects.append(spec.PGCObject(pgc=obj.pgc, catalogs=result))

        return spec.QuerySimpleResponse(objects=pgc_objects, schema=catalog_schema)

    def build_response(self, objects: list[model.Layer2Object]) -> Any:
        catalog_schema = DATA_SCHEMA
        pgc_objects: list[spec.PGCObject] = []
        corrected_photometry_by_pgc = self._fetch_corrected_photometry(objects)

        for obj in objects:
            catalogs = spec.Catalogs()

            if obj.catalogs.designation is not None:
                catalogs.designation = spec.Designation(name=obj.catalogs.designation.name)

            if obj.catalogs.additional_designations is not None:
                catalogs.additional_designations = [
                    spec.AdditionalDesignation(
                        name=ad.name,
                        source=spec.Source(
                            bibcode=ad.source.bibcode,
                            title=ad.source.title,
                            authors=ad.source.authors,
                            year=ad.source.year,
                        ),
                    )
                    for ad in obj.catalogs.additional_designations.names
                ]

            icrs = obj.catalogs.icrs
            if icrs is not None:
                catalogs.coordinates = _coordinates_from_icrs(icrs.ra, icrs.dec, icrs.e_ra, icrs.e_dec)

            if obj.catalogs.redshift is not None:
                redshift = obj.catalogs.redshift
                catalogs.redshift = _redshift_from_cz(redshift.cz, redshift.e_cz)

            if obj.catalogs.nature is not None:
                catalogs.nature = spec.Nature(type_name=obj.catalogs.nature.type_name)

            if obj.catalogs.morphology is not None:
                catalogs.morphology = spec.Morphology(
                    t=obj.catalogs.morphology.t,
                    em=obj.catalogs.morphology.em,
                    ep=obj.catalogs.morphology.ep,
                )

            if obj.catalogs.notes is not None:
                catalogs.notes = [
                    spec.NoteEntry(
                        note=note.note,
                        source=spec.Source(
                            bibcode=note.source.bibcode,
                            title=note.source.title,
                            authors=note.source.authors,
                            year=note.source.year,
                        ),
                    )
                    for note in obj.catalogs.notes.notes
                ]

            if obj.catalogs.photometry_total is not None:
                catalogs.photometry_total = [
                    _photometry_total_measurement(measurement)
                    for measurement in obj.catalogs.photometry_total.measurements
                ]

            if corrected_photometry := corrected_photometry_by_pgc.get(obj.pgc):
                catalogs.photometry_total_corrected = corrected_photometry

            if obj.catalogs.velocity:
                catalogs.velocity = _velocities_from_stored(obj.catalogs.velocity, catalog_schema)

            pgc_objects.append(spec.PGCObject(pgc=obj.pgc, catalogs=catalogs))

        return spec.QuerySimpleResponse(objects=pgc_objects, schema=catalog_schema)
