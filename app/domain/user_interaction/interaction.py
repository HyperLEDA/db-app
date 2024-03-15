from abc import ABC, abstractmethod

from .interaction_argument import (
    AbstractArgument,
    ResolveCoordinateParseFailArg,
    ResolveCrossIdentificationCollisionInteractionArg,
)
from .interaction_result import (
    InteractionResult,
    ResolveCrossIdentificationCollisionInteractionRes,
)


class AbstractInteraction(ABC):
    """
    Represents an interaction with User. The interaction has an argument and result, that is obtained by evaluating the
    'eval' method
    """

    @abstractmethod
    async def eval(self, arg: AbstractArgument) -> InteractionResult:
        pass


class ResolveCrossIdentificationCollisionInteraction(AbstractInteraction):
    @abstractmethod
    async def eval(self) -> ResolveCrossIdentificationCollisionInteractionRes:
        # TODO implement
        pass


class ResolveCoordinateParseFail(AbstractInteraction):
    @abstractmethod
    async def eval(self, arg: ResolveCoordinateParseFailArg) -> InteractionResult:
        pass
