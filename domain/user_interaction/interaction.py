from abc import ABC, abstractmethod

from .interaction_argument import AbstractArgument, ResolveCrossIdentificationCollisionInteractionArg, \
    ResolveCoordinateParseFailArg, Confirm01TransactionArg
from .interaction_result import InteractionResult, ResolveCrossIdentificationCollisionInteractionRes, \
    ResolveCoordinateParseFailRes, Confirm01TransactionRes


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
    async def eval(
            self,
            arg: ResolveCrossIdentificationCollisionInteractionArg
    ) -> ResolveCrossIdentificationCollisionInteractionRes:
        pass


class ResolveCoordinateParseFail(AbstractInteraction):
    @abstractmethod
    async def eval(self, arg: ResolveCoordinateParseFailArg) -> ResolveCoordinateParseFailRes:
        pass


class Confirm01Transaction(AbstractInteraction):
    @abstractmethod
    async def eval(self, arg: Confirm01TransactionArg) -> Confirm01TransactionRes:
        pass
