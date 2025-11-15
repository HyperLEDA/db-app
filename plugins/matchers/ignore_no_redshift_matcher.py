from typing import final

from app.data import model
from app.domain.unification.crossmatch import CIMatcher


@final
class IgnoreNoRedshiftMatcher:
    def __init__(self, matcher: CIMatcher):
        self.matcher = matcher

    def __call__(self, record1: model.Record, record2: model.Layer2Object) -> float:
        redshift1 = record1.get(model.RedshiftCatalogObject)
        redshift2 = record2.get(model.RedshiftCatalogObject)

        if redshift1 is None or redshift2 is None:
            return 1.0

        return self.matcher(record1, record2)


def ignore_no_redshift_matcher(matcher: CIMatcher) -> CIMatcher:
    return IgnoreNoRedshiftMatcher(matcher)


name = "ignore_no_redshift"
plugin = ignore_no_redshift_matcher
