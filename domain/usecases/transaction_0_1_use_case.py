from typing import Callable, Optional, Union
from dataclasses import replace

from . import TransformationO1UseCase, CrossIdentifyUseCase
from .exceptions import CrossIdentificationException
from ..model import Layer0Model, Layer1Model
from ..model.layer0 import Transformation01Fail
from ..model.params import CrossIdentificationParam
from ..model.params.transaction_0_1_stages import TransactionO1Sage, AwaitingQueue, TransformingData
from ..repositories.layer_0_repository import Layer0Repository
from ..repositories.layer_1_repository import Layer1Repository
from ..user_interaction.interaction import ResolveCoordinateParseFail, ResolveCrossIdentificationCollisionInteraction
from ..user_interaction.interaction_argument import ResolveCoordinateParseFailArg, \
    ResolveCrossIdentificationCollisionInteractionArg
from ..user_interaction.interaction_result import ResolveCoordinateParseFailRes, \
    ResolveCrossIdentificationCollisionInteractionRes, CollisionSkipped, CollisionCanceled, CollisionNewObject, \
    CollisionObjectSelected
from ..util import GlobalDBLock


class Transaction01UseCase:
    """
    Performs data transaction from layer 0 to layer 1
    """
    def __init__(
            self,
            transformation_use_case: TransformationO1UseCase,
    ):
        self._transformation_use_case: TransformationO1UseCase = transformation_use_case

    async def invoke(
            self,
            data: Layer0Model,
            on_progress: Optional[Callable[[TransactionO1Sage], None]] = None
    ) -> tuple[Layer0Model, list[Layer1Model], list[Transformation01Fail]]:
        """
        :param data: Layer 0 data to be transformed
        :param on_progress: Function, called on pogress
        :return:
            updated_source: Updated Layer 0 data (according to transformation result)
            updated_models: Successfully transformed Layer 1 data
            fails: Fails during transformation
        """
        if on_progress is not None:
            on_progress(AwaitingQueue())

        async with GlobalDBLock.get():
            return await self._perform_transaction(data, on_progress)

    async def _perform_transaction(
            self,
            data: Layer0Model,
            on_progress: Optional[Callable[[TransactionO1Sage], None]]
    ) -> tuple[Layer0Model, list[Layer1Model], list[Transformation01Fail]]:
        if on_progress is not None:
            models, fails = await self._transformation_use_case.invoke(
                data,
                lambda stage: on_progress(TransformingData(stage))
            )
        else:
            models, fails = await self._transformation_use_case.invoke(data)

        updated_source, updated_models = self._update_update_time(data, models)

        return updated_source, updated_models, fails

    def _update_update_time(
            self,
            source: Layer0Model,
            models: list[Layer1Model]
    ) -> tuple[Layer0Model, list[Layer1Model]]:
        """
        Update info about data frame last processing
        :param source: Source of data, being transformed
        :param models: Successfully processed models
        :return: updated source and models
        """
        updated_source = replace(source, processed=True)
        return updated_source, models
