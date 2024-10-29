from abc import ABC, abstractmethod

from app.domain.user_interaction.interaction_argument import (
    AbstractArgument,
    Confirm01TransactionArg,
    ResolveCoordinateParseFailArg,
    ResolveCrossIdentificationCollisionInteractionArg,
)
from app.domain.user_interaction.interaction_result import (
    Confirm01TransactionRes,
    InteractionResult,
    ResolveCoordinateParseFailRes,
    ResolveCrossIdentificationCollisionInteractionRes,
)


class AbstractInteraction(ABC):
    """
    Represents an interaction with User. The interaction has an argument and result, that is obtained by evaluating the
    'eval' method
    """

    @abstractmethod
    def eval(self, arg: AbstractArgument) -> InteractionResult:
        pass


class ResolveCrossIdentificationCollisionInteraction(AbstractInteraction):
    @abstractmethod
    def eval(
        self, arg: ResolveCrossIdentificationCollisionInteractionArg
    ) -> ResolveCrossIdentificationCollisionInteractionRes:
        pass


class ResolveCoordinateParseFail(AbstractInteraction):
    @abstractmethod
    def eval(self, arg: ResolveCoordinateParseFailArg) -> ResolveCoordinateParseFailRes:
        pass


class Confirm01Transaction(AbstractInteraction):
    @abstractmethod
    def eval(self, arg: Confirm01TransactionArg) -> Confirm01TransactionRes:
        pass
