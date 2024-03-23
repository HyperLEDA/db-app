from abc import ABC


class InteractionResult(ABC):
    pass


class ResolveCrossIdentificationCollisionInteractionRes(InteractionResult):
    pass


class ResolveCoordinateParseFailRes(InteractionResult):
    def __init__(self, is_cancelled: bool):
        self.is_cancelled: bool = is_cancelled
