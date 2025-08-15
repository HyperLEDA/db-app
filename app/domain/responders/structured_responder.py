from typing import Any

from astropy import constants
from astropy import coordinates as coords
from astropy import units as u

from app.data import model
from app.data.model import layer2
from app.domain.responders import interface
from app.lib import astronomy, config
from app.presentation import dataapi


class ApexConfig(config.BaseConfigSettings):
    lon: float
    lat: float
    vel: float


class VelocityCatalogConfig(config.BaseConfigSettings):
    apexes: dict[str, ApexConfig]


class CatalogConfig(config.BaseConfigSettings):
    velocity: VelocityCatalogConfig


class StructuredResponder(interface.ObjectResponder):
    def __init__(self, cfg: CatalogConfig) -> None:
        self.config = cfg

    def _heliocentric_to_redshift(self, cz: float) -> float:
        return ((cz * u.Unit("m") / u.Unit("s")) / constants.c).value

    def _equatorial(
        self,
        ra: float,
        dec: float,
        e_ra: float,
        e_dec: float,
    ) -> tuple[float, float, float, float]:
        e_ra = (e_ra * u.Unit("deg")).to(u.Unit("arcsec")).value
        e_dec = (e_dec * u.Unit("deg")).to(u.Unit("arcsec")).value

        return ra, dec, e_ra, e_dec

    def _equatorial_to_galactic(
        self, ra: float, dec: float, e_ra: float, e_dec: float
    ) -> tuple[float, float, float, float]:
        coord = coords.SkyCoord(ra=ra * u.Unit("deg"), dec=dec * u.Unit("deg"))
        gal = coord.galactic

        # TODO: for simplicity this approach assumes errors in galactic coordinates to be the
        # same, which might not necessarily be true for larger erros.
        lon = gal.l.to(u.Unit("deg")).value
        lat = gal.b.to(u.Unit("deg")).value
        e_lon = (e_ra * u.Unit("deg")).to(u.Unit("arcsec")).value
        e_lat = (e_dec * u.Unit("deg")).to(u.Unit("arcsec")).value

        return lon, lat, e_lon, e_lat

    def build_response(self, objects: list[layer2.Layer2Object]) -> Any:
        pgc_objects = []

        for obj in objects:
            catalogs = dataapi.Catalogs()

            if (designation := obj.get(model.DesignationCatalogObject)) is not None:
                catalogs.designation = dataapi.Designation(name=designation.designation)

            icrs = obj.get(model.ICRSCatalogObject)
            if icrs is not None:
                ra, dec, e_ra, e_dec = self._equatorial(icrs.ra, icrs.dec, icrs.e_ra, icrs.e_dec)
                lon, lat, e_lon, e_lat = self._equatorial_to_galactic(icrs.ra, icrs.dec, icrs.e_ra, icrs.e_dec)

                catalogs.coordinates = dataapi.Coordinates(
                    equatorial=dataapi.EquatorialCoordinates(ra=ra, dec=dec, e_ra=e_ra, e_dec=e_dec),
                    galactic=dataapi.GalacticCoordinates(lon=lon, lat=lat, e_lon=e_lon, e_lat=e_lat),
                )

            redshift = obj.get(model.RedshiftCatalogObject)
            if redshift is not None:
                catalogs.redshift = dataapi.Redshift(
                    z=self._heliocentric_to_redshift(redshift.cz),
                    e_z=self._heliocentric_to_redshift(redshift.e_cz),
                )

            if icrs is not None and redshift is not None:
                catalogs.velocity = {}

                for key, apex in self.config.velocity.apexes.items():
                    vel_wr_apex = astronomy.velocity_wr_apex(
                        redshift.cz * u.Unit("m/s"),
                        lon=lon * u.Unit("deg"),
                        lat=lat * u.Unit("deg"),
                        vel_apex=apex.vel * u.Unit("km/s"),
                        lon_apex=apex.lon * u.Unit("deg"),
                        lat_apex=apex.lat * u.Unit("deg"),
                    )

                    catalogs.velocity[key] = dataapi.AbsoluteVelocity(
                        v=vel_wr_apex.to(u.Unit("km/s")).value,
                        e_v=redshift.e_cz,
                    )

            pgc_object = dataapi.PGCObject(pgc=obj.pgc, catalogs=catalogs)
            pgc_objects.append(pgc_object)

        return pgc_objects
