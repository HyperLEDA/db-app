from typing import final

from astropy import coordinates
from astropy import units as u

from app.data.model import icrs, layer0, layer2
from app.domain.unification.crossmatch import CIMatcher


@final
class CircleMatcher:
    def __init__(self, radius_arcsec: float):
        self.radius_arcsec = radius_arcsec

    def __call__(self, object1: layer0.Layer0Object, object2: layer2.Layer2Object) -> float:
        coords1 = object1.get(icrs.ICRSCatalogObject)
        coords2 = object2.get(icrs.ICRSCatalogObject)

        if coords1 is None or coords2 is None:
            return 0.0

        acoords1 = coordinates.SkyCoord(ra=coords1.ra, dec=coords1.dec)
        acoords2 = coordinates.SkyCoord(ra=coords2.ra, dec=coords2.dec)

        sep = acoords1.separation(acoords2)

        distance_arcsec = sep.to(u.Unit("arcsec")).value

        if distance_arcsec <= self.radius_arcsec:
            return 1.0
        return 0.0


def circle_matcher(radius_arcsec: float) -> CIMatcher:
    return CircleMatcher(radius_arcsec)


name = "circle"
plugin = circle_matcher
