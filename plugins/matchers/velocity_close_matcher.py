from typing import final

from app.data.model import layer0, layer2, redshift
from app.domain.unification.crossmatch import CIMatcher


@final
class VelocityCloseMatcher:
    def __init__(self, velocity_variance: float):
        self.velocity_variance = velocity_variance

    def __call__(self, object1: layer0.Layer0Object, object2: layer2.Layer2Object) -> float:
        redshift1 = object1.get(redshift.RedshiftCatalogObject)
        redshift2 = object2.get(redshift.RedshiftCatalogObject)

        if redshift1 is None or redshift2 is None:
            return 0.0

        cz_diff = abs(redshift1.cz - redshift2.cz)

        if cz_diff <= self.velocity_variance:
            return 1.0
        return 0.0


def velocity_close_matcher(velocity_variance: float) -> CIMatcher:
    return VelocityCloseMatcher(velocity_variance)


name = "velocity_close"
plugin = velocity_close_matcher
