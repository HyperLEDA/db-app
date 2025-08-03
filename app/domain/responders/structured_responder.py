from typing import Any

from astropy import constants
from astropy import units as u

from app.data import model
from app.data.model import layer2
from app.domain.responders import interface
from app.presentation.dataapi.model import (
    Catalogs,
    Coordinates,
    Designation,
    EquatorialCoordinates,
    GalacticCoordinates,
    HeliocentricVelocity,
    PGCObject,
    Redshift,
    Velocity,
)


class StructuredResponder(interface.ObjectResponder):
    def _heliocentric_to_redshift(self, cz: float) -> float:
        return (cz * u.m / u.s) / constants.c

    def build_response(self, objects: list[layer2.Layer2Object]) -> Any:
        pgc_objects = []

        for obj in objects:
            catalogs = Catalogs()

            if (designation := obj.get(model.DesignationCatalogObject)) is not None:
                catalogs.designation = Designation(name=designation.designation)

            if (icrs := obj.get(model.ICRSCatalogObject)) is not None:
                catalogs.coordinates = Coordinates(
                    equatorial=EquatorialCoordinates(ra=icrs.ra, dec=icrs.dec, e_ra=icrs.e_ra, e_dec=icrs.e_dec),
                    galactic=GalacticCoordinates(lon=0.0, lat=0.0, e_lon=0.0, e_lat=0.0),
                )

            if (redshift := obj.get(model.RedshiftCatalogObject)) is not None:
                catalogs.velocity = Velocity(
                    heliocentric=HeliocentricVelocity(v=redshift.cz, e_v=redshift.e_cz),
                    redshift=Redshift(
                        z=self._heliocentric_to_redshift(redshift.cz),
                        e_z=self._heliocentric_to_redshift(redshift.e_cz),
                    ),
                )

            pgc_object = PGCObject(pgc=obj.pgc, catalogs=catalogs)
            pgc_objects.append(pgc_object)

        return pgc_objects
