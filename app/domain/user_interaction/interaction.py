from abc import ABC, abstractmethod

from app.domain.user_interaction.interaction_argument import AbstractArgument
from app.domain.user_interaction.interaction_result import InteractionResult


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
    async def eval(self, arg: AbstractArgument) -> InteractionResult:
        # TODO implement
        pass


class ResolveCoordinateParseFail(AbstractInteraction):
    @abstractmethod
    async def eval(self, arg: AbstractArgument) -> InteractionResult:
        pass
