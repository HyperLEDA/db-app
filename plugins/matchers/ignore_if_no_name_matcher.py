from typing import final

from app.data.model import designation, layer0, layer2
from app.domain.unification.crossmatch import CIMatcher


@final
class IgnoreIfNoNameMatcher:
    def __init__(self, matcher: CIMatcher):
        self.matcher = matcher

    def __call__(self, object1: layer0.Layer0Object, object2: layer2.Layer2Object) -> float:
        name1 = object1.get(designation.DesignationCatalogObject)
        name2 = object2.get(designation.DesignationCatalogObject)

        if name1 is None or name2 is None:
            return 1.0

        return self.matcher(object1, object2)


def ignore_if_no_name_matcher(matcher: CIMatcher) -> CIMatcher:
    return IgnoreIfNoNameMatcher(matcher)


name = "ignore_if_no_name"
plugin = ignore_if_no_name_matcher
