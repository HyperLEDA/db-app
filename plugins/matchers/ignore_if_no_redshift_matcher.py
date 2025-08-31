from typing import final

from app.data.model import layer0, layer2, redshift
from app.domain.unification.crossmatch import CIMatcher


@final
class IgnoreIfNoRedshiftMatcher:
    def __init__(self, matcher: CIMatcher):
        self.matcher = matcher

    def __call__(self, object1: layer0.Layer0Object, object2: layer2.Layer2Object) -> float:
        redshift1 = object1.get(redshift.RedshiftCatalogObject)
        redshift2 = object2.get(redshift.RedshiftCatalogObject)

        if redshift1 is None or redshift2 is None:
            return 1.0

        return self.matcher(object1, object2)


def ignore_if_no_redshift_matcher(matcher: CIMatcher) -> CIMatcher:
    return IgnoreIfNoRedshiftMatcher(matcher)


name = "ignore_if_no_redshift"
plugin = ignore_if_no_redshift_matcher
