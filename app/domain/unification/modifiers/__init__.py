from app.domain.unification.modifiers.apply import Applicator
from app.domain.unification.modifiers.interface import (
    AddUnitColumnModifier,
    ColumnModifier,
    FormatColumnModifier,
    MapColumnModifier,
)

registry: dict[str, type[ColumnModifier]] = {
    mod.name(): mod for mod in [MapColumnModifier, FormatColumnModifier, AddUnitColumnModifier]
}

__all__ = [
    "ColumnModifier",
    "MapColumnModifier",
    "FormatColumnModifier",
    "AddUnitColumnModifier",
    "Applicator",
    "registry",
]
