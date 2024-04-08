from abc import ABC

from app.domain.model import Layer0Model


class InteractionResult(ABC):
    pass


class ResolveCrossIdentificationCollisionInteractionRes(InteractionResult):
    pass


class CollisionSkipped(ResolveCrossIdentificationCollisionInteractionRes):
    pass


class CollisionNewObject(ResolveCrossIdentificationCollisionInteractionRes):
    pass


class CollisionCanceled(ResolveCrossIdentificationCollisionInteractionRes):
    pass


class CollisionObjectSelected(ResolveCrossIdentificationCollisionInteractionRes):
    def __init__(self, selected_object: Layer0Model):
        self.selected_object: Layer0Model = selected_object


class ResolveCoordinateParseFailRes(InteractionResult):
    def __init__(self, is_cancelled: bool):
        self.is_cancelled: bool = is_cancelled


class Confirm01TransactionRes(InteractionResult):
    def __init__(self, is_confirmed: bool):
        self._is_confirmed = is_confirmed
