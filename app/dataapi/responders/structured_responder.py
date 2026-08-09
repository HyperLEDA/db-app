from typing import Any

from astropy import units as u

from app.data import model
from app.data.model import layer2
from app.dataapi import presentation as dataapi
from app.dataapi.responders import interface
from app.lib import astronomy, config

DATA_SCHEMA = dataapi.Schema(
    units=dataapi.Units(
        coordinates=dataapi.CoordinateUnits(
            equatorial=dataapi.EquatorialCoordinatesUnits(
                ra="deg",
                dec="deg",
                e_ra="arcsec",
                e_dec="arcsec",
            ),
            galactic=dataapi.GalacticCoordinatesUnits(
                lon="deg",
                lat="deg",
                e_lon="arcsec",
                e_lat="arcsec",
            ),
            supergalactic=dataapi.SupergalacticCoordinatesUnits(
                lon="deg",
                lat="deg",
                e_lon="arcsec",
                e_lat="arcsec",
            ),
        ),
        velocity={},
    )
)

VELOCITY_SCHEMA = dataapi.AbsoluteVelocityUnits(
    v="km/s",
    e_v="km/s",
)


class ValueWithUncertainty(config.BaseConfigSettings):
    value: float
    error: float


class ApexConfig(config.BaseConfigSettings):
    lon: ValueWithUncertainty
    lat: ValueWithUncertainty
    vel: ValueWithUncertainty


class VelocityCatalogConfig(config.BaseConfigSettings):
    apexes: dict[str, ApexConfig]


class CatalogConfig(config.BaseConfigSettings):
    velocity: VelocityCatalogConfig


class StructuredResponder(interface.ObjectResponder):
    def __init__(self, cfg: CatalogConfig) -> None:
        self.config = cfg

    def _coordinates_from_icrs(self, ra: float, dec: float, e_ra: float, e_dec: float) -> dataapi.Coordinates:
        eq_e_ra = astronomy.to(e_ra * u.Unit("deg"), "arcsec")
        eq_e_dec = astronomy.to(e_dec * u.Unit("deg"), "arcsec")
        lon, lat, e_lon, e_lat = astronomy.equatorial_to_lonlat(ra, dec, e_ra, e_dec, "galactic")
        sg_lon, sg_lat, sg_e_lon, sg_e_lat = astronomy.equatorial_to_lonlat(ra, dec, e_ra, e_dec, "supergalactic")
        return dataapi.Coordinates(
            equatorial=dataapi.EquatorialCoordinates(ra=ra, dec=dec, e_ra=eq_e_ra, e_dec=eq_e_dec),
            galactic=dataapi.GalacticCoordinates(lon=lon, lat=lat, e_lon=e_lon, e_lat=e_lat),
            supergalactic=dataapi.SupergalacticCoordinates(lon=sg_lon, lat=sg_lat, e_lon=sg_e_lon, e_lat=sg_e_lat),
        )

    def _redshift_from_cz(self, cz: float, e_cz: float) -> dataapi.Redshift:
        return dataapi.Redshift(
            z=astronomy.heliocentric_cz_to_z(cz * u.Unit("km/s")),
            e_z=astronomy.heliocentric_cz_to_z(e_cz * u.Unit("km/s")),
        )

    def _velocities_from_apexes(
        self,
        lon: float,
        lat: float,
        e_lon: float,
        e_lat: float,
        cz: float,
        e_cz: float,
        catalog_schema: dataapi.Schema,
    ) -> dict[str, dataapi.AbsoluteVelocity]:
        velocities: dict[str, dataapi.AbsoluteVelocity] = {}
        for key, apex in self.config.velocity.apexes.items():
            vel_wr_apex, vel_wr_apex_err = astronomy.velocity_wr_apex(
                vel=cz * u.Unit("km/s"),
                lon=lon * u.Unit("deg"),
                lat=lat * u.Unit("deg"),
                vel_apex=apex.vel.value * u.Unit("km/s"),
                lon_apex=apex.lon.value * u.Unit("deg"),
                lat_apex=apex.lat.value * u.Unit("deg"),
                vel_err=e_cz * u.Unit("km/s"),
                lon_err=e_lon * u.Unit("arcsec"),
                lat_err=e_lat * u.Unit("arcsec"),
                vel_apex_err=apex.vel.error * u.Unit("km/s"),
                lon_apex_err=apex.lon.error * u.Unit("deg"),
                lat_apex_err=apex.lat.error * u.Unit("deg"),
            )

            schema = VELOCITY_SCHEMA
            catalog_schema.units.velocity[key] = schema
            velocities[key] = dataapi.AbsoluteVelocity(
                v=vel_wr_apex.to(u.Unit(schema.v)).value,
                e_v=vel_wr_apex_err.to(u.Unit(schema.e_v)).value,
            )
        return velocities

    def build_response_from_catalog(self, objects: list[layer2.Layer2CatalogObject]) -> Any:
        catalog_schema = DATA_SCHEMA
        pgc_objects = []

        for obj in objects:
            catalogs = dataapi.Catalogs()

            if (designation := obj.get(model.DesignationCatalogObject)) is not None:
                catalogs.designation = dataapi.Designation(name=designation.designation)

            icrs = obj.get(model.ICRSCatalogObject)
            if icrs is not None:
                catalogs.coordinates = self._coordinates_from_icrs(icrs.ra, icrs.dec, icrs.e_ra, icrs.e_dec)

            redshift = obj.get(model.RedshiftCatalogObject)
            if redshift is not None:
                catalogs.redshift = self._redshift_from_cz(redshift.cz, redshift.e_cz)

            if (nature := obj.get(model.NatureCatalogObject)) is not None:
                catalogs.nature = dataapi.Nature(type_name=nature.type_name)

            if icrs is not None and redshift is not None and catalogs.coordinates is not None:
                gal = catalogs.coordinates.galactic
                catalogs.velocity = self._velocities_from_apexes(
                    gal.lon,
                    gal.lat,
                    gal.e_lon,
                    gal.e_lat,
                    redshift.cz,
                    redshift.e_cz,
                    catalog_schema,
                )

            pgc_objects.append(dataapi.PGCObject(pgc=obj.pgc, catalogs=catalogs))

        return dataapi.QuerySimpleResponse(objects=pgc_objects, schema=catalog_schema)

    def build_response(self, objects: list[layer2.Layer2Object]) -> Any:
        catalog_schema = DATA_SCHEMA
        pgc_objects = []

        for obj in objects:
            catalogs = dataapi.Catalogs()

            if obj.catalogs.designation is not None:
                catalogs.designation = dataapi.Designation(name=obj.catalogs.designation.name)

            if obj.catalogs.additional_designations is not None:
                catalogs.additional_designations = [
                    dataapi.AdditionalDesignation(
                        name=ad.name,
                        source=dataapi.Source(
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
                catalogs.coordinates = self._coordinates_from_icrs(icrs.ra, icrs.dec, icrs.e_ra, icrs.e_dec)

            if obj.catalogs.redshift is not None:
                redshift = obj.catalogs.redshift
                catalogs.redshift = self._redshift_from_cz(redshift.cz, redshift.e_cz)

            if obj.catalogs.nature is not None:
                catalogs.nature = dataapi.Nature(type_name=obj.catalogs.nature.type_name)

            if obj.catalogs.notes is not None:
                catalogs.notes = [
                    dataapi.NoteEntry(
                        note=note.note,
                        source=dataapi.Source(
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
                    dataapi.PhotometryTotalMeasurement(
                        band=measurement.band,
                        magsys=measurement.magsys,
                        method=measurement.method,
                        wavelength=measurement.wavelength,
                        mag=measurement.mag,
                        e_mag=measurement.e_mag,
                    )
                    for measurement in obj.catalogs.photometry_total.measurements
                ]

            if icrs is not None and obj.catalogs.redshift is not None and catalogs.coordinates is not None:
                redshift = obj.catalogs.redshift
                gal = catalogs.coordinates.galactic
                catalogs.velocity = self._velocities_from_apexes(
                    gal.lon,
                    gal.lat,
                    gal.e_lon,
                    gal.e_lat,
                    redshift.cz,
                    redshift.e_cz,
                    catalog_schema,
                )

            pgc_objects.append(dataapi.PGCObject(pgc=obj.pgc, catalogs=catalogs))

        return dataapi.QuerySimpleResponse(objects=pgc_objects, schema=catalog_schema)
