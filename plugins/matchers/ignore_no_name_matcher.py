from typing import final

from app.data import model
from app.domain.unification.crossmatch import CIMatcher


@final
class IgnoreNoNameMatcher:
    def __init__(self, matcher: CIMatcher):
        self.matcher = matcher

    def __call__(self, record1: model.Record, record2: model.Layer2Object) -> float:
        name1 = record1.get(model.DesignationCatalogObject)
        name2 = record2.get(model.DesignationCatalogObject)

        if name1 is None or name2 is None:
            return 1.0

        return self.matcher(record1, record2)


def ignore_no_name_matcher(matcher: CIMatcher) -> CIMatcher:
    return IgnoreNoNameMatcher(matcher)


name = "ignore_no_name"
plugin = ignore_no_name_matcher
