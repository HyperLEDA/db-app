from typing import final

from app.data import model
from app.domain.unification.crossmatch import CIMatcher


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


@final
class LevenshteinMatcher:
    def __init__(self, max_distance: int):
        self.max_distance = max_distance

    def __call__(self, record1: model.Record, record2: model.Layer2Object) -> float:
        name1 = record1.get(model.DesignationCatalogObject)
        name2 = record2.get(model.DesignationCatalogObject)

        if name1 is None or name2 is None:
            return 0.0

        distance = levenshtein_distance(name1.designation, name2.designation)

        if distance <= self.max_distance:
            if distance == 0:
                return 1.0
            return 1.0 - (distance / self.max_distance)
        return 0.0


def levenshtein_matcher(max_distance: int) -> CIMatcher:
    return LevenshteinMatcher(max_distance)


name = "levenshtein"
plugin = levenshtein_matcher
