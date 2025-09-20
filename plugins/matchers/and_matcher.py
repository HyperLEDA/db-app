from typing import final

from app.data import model
from app.domain.unification.crossmatch import CIMatcher


@final
class AndMatcher:
    def __init__(self, matcher1: CIMatcher, matcher2: CIMatcher):
        self.matcher1 = matcher1
        self.matcher2 = matcher2

    def __call__(self, record1: model.Record, record2: model.Layer2Object) -> float:
        prob1 = self.matcher1(record1, record2)
        prob2 = self.matcher2(record1, record2)
        return prob1 * prob2


def and_matcher(matcher1: CIMatcher, matcher2: CIMatcher) -> CIMatcher:
    return AndMatcher(matcher1, matcher2)


name = "and"
plugin = and_matcher
