import itertools
import re
from collections.abc import Sequence

import numpy as np
from astropy import table

from app.tasks import layer2_common

# Patterns must be valid for both Python re.fullmatch and PostgreSQL POSIX regex (~).
PRIORITY_MASKS = [
    r"(And|Cas|Tri) [0-9]+",
    r"M [0-9]+",
    r"IC [0-9]+[A-Z]?",
    r"NGC [0-9]+[A-Z]?",
    r"UGC [0-9]+[A-Z]?",
    r"PGC [0-9]+",
]


def aggregate_designation(
    tbl: table.QTable,
    priority_masks: Sequence[str] | None = None,
) -> table.QTable:
    masks = PRIORITY_MASKS if priority_masks is None else priority_masks
    grouped = tbl.group_by("pgc")
    selected = np.zeros(len(grouped), dtype=bool)

    for start, stop in itertools.pairwise(grouped.groups.indices):
        designations = np.asarray(grouped["design"][start:stop], dtype=str)
        for mask in masks:
            matches = np.fromiter(
                (re.fullmatch(mask, name) is not None for name in designations),
                dtype=bool,
                count=len(designations),
            )
            if np.any(matches):
                selected[start:stop] = matches
                break
        else:
            selected[start:stop] = True

    pgcs, designs = layer2_common.majority_vote_by_pgc(grouped[selected], "design")
    return table.QTable({"pgc": pgcs, "design": designs})
