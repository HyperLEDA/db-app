from typing import final

from app.data.model import layer0, layer2
from plugins.ci_types import CIMatcher


@final
class AndMatcher:
    def __init__(self, matcher1: CIMatcher, matcher2: CIMatcher):
        self.matcher1 = matcher1
        self.matcher2 = matcher2

    def __call__(self, object1: layer0.Layer0Object, object2: layer2.Layer2Object) -> float:
        prob1 = self.matcher1(object1, object2)
        prob2 = self.matcher2(object1, object2)
        return prob1 * prob2


def and_matcher(matcher1: CIMatcher, matcher2: CIMatcher) -> CIMatcher:
    return AndMatcher(matcher1, matcher2)


name = "and"
matcher = and_matcher
