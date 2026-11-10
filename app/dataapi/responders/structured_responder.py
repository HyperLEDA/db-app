from typing import Any, override

from astropy import units as u

from app.catalogs import layer2
from app.dataapi import model
from app.dataapi.domain import reddening
from app.dataapi.responders import interface
from app.lib import astronomy
from app.specs import dataapi as spec

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


def _coordinates_from_objects(obj: model.ObjectsCatalog) -> spec.Coordinates | None:
    if (
        obj.ra is None
        or obj.e_ra is None
        or obj.dec is None
        or obj.e_dec is None
        or obj.galactic_l is None
        or obj.galactic_b is None
        or obj.sgl is None
        or obj.sgb is None
    ):
        return None
    eq_e_ra = astronomy.to(obj.e_ra * u.Unit("deg"), "arcsec")
    eq_e_dec = astronomy.to(obj.e_dec * u.Unit("deg"), "arcsec")
    return spec.Coordinates(
        equatorial=spec.EquatorialCoordinates(ra=obj.ra, dec=obj.dec, e_ra=eq_e_ra, e_dec=eq_e_dec),
        galactic=spec.GalacticCoordinates(lon=obj.galactic_l, lat=obj.galactic_b, e_lon=eq_e_ra, e_lat=eq_e_dec),
        supergalactic=spec.SupergalacticCoordinates(lon=obj.sgl, lat=obj.sgb, e_lon=eq_e_ra, e_lat=eq_e_dec),
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
        correction_work: list[tuple[int, float, list[model.PhotometryTotalMeasurement]]] = []
        photsys_values: set[str] = set()
        for obj in objects:
            if obj.catalogs.photometry_total is None or obj.catalogs.objects is None:
                continue
            ebv = obj.catalogs.objects.ebv
            if ebv is None:
                continue
            measurements = obj.catalogs.photometry_total.measurements
            correction_work.append((obj.pgc, ebv, measurements))
            photsys_values.update(measurement.photsys for measurement in measurements)

        if not correction_work:
            return {}

        a_ebv_by_photsys = {photsys: self.reddening_service.a_ebv_by_filter(photsys) for photsys in photsys_values}

        corrected_by_pgc: dict[int, list[spec.PhotometryTotalMeasurement]] = {}
        for pgc, ebv, measurements in correction_work:
            corrected: list[spec.PhotometryTotalMeasurement] = []
            for measurement in measurements:
                a_ebv = a_ebv_by_photsys.get(measurement.photsys, {}).get(measurement.filter)
                if a_ebv is None:
                    continue
                corrected.append(
                    spec.PhotometryTotalMeasurement(
                        band=measurement.band,
                        magsys=measurement.magsys,
                        method=measurement.method,
                        wavelength=measurement.wavelength,
                        mag=measurement.mag - a_ebv * ebv,
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

            objects_catalog = obj.get(layer2.ObjectsCatalogObject)
            if objects_catalog is not None:
                result.coordinates = _coordinates_from_objects(
                    model.ObjectsCatalog(
                        ra=objects_catalog.ra,
                        e_ra=objects_catalog.e_ra,
                        dec=objects_catalog.dec,
                        e_dec=objects_catalog.e_dec,
                        galactic_l=objects_catalog.l,
                        galactic_b=objects_catalog.b,
                        sgl=objects_catalog.sgl,
                        sgb=objects_catalog.sgb,
                        ebv=objects_catalog.ebv,
                    )
                )

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

            if obj.catalogs.objects is not None:
                catalogs.coordinates = _coordinates_from_objects(obj.catalogs.objects)

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
