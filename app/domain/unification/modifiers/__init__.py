from app.domain.unification.modifiers.apply import Applicator
from app.domain.unification.modifiers.interface import (
    AddUnitColumnModifier,
    ColumnModifier,
    ConstantColumnModifier,
    FormatColumnModifier,
    MapColumnModifier,
)

registry: dict[str, type[ColumnModifier]] = {
    mod.name(): mod for mod in [MapColumnModifier, FormatColumnModifier, AddUnitColumnModifier, ConstantColumnModifier]
}

__all__ = [
    "ColumnModifier",
    "MapColumnModifier",
    "FormatColumnModifier",
    "AddUnitColumnModifier",
    "ConstantColumnModifier",
    "Applicator",
    "registry",
]
