from dataclasses import replace
from typing import Callable, Optional

from ..model import Layer0Model, Layer1Model
from ..model.params.transaction_0_1_stages import (
    AwaitingQueue,
    TransactionO1Sage,
    TransformingData,
)
from ..repositories.layer_0_repository import Layer0Repository
from ..repositories.layer_1_repository import Layer1Repository
from ..user_interaction.interaction import ResolveCoordinateParseFail
from ..user_interaction.interaction_argument import ResolveCoordinateParseFailArg
from ..user_interaction.interaction_result import ResolveCoordinateParseFailRes
from ..util import GlobalDBLock
from . import TransformationO1UseCase
from .exceptions import CrossIdentificationException


class Transaction01UseCase:
    """
    Performs data transaction from layer 0 to layer 1
    """

    def __init__(
        self,
        transformation_use_case: TransformationO1UseCase,
        layer_0_repository: Layer0Repository,
        layer_1_repository: Layer1Repository,
        resolve_coordinate_parse_fail: ResolveCoordinateParseFail,
    ):
        self._transformation_use_case: TransformationO1UseCase = transformation_use_case
        self._layer_0_repository: Layer0Repository = layer_0_repository
        self._layer_1_repository: Layer1Repository = layer_1_repository
        self._resolve_coordinate_parse_fail: ResolveCoordinateParseFail = resolve_coordinate_parse_fail

    async def invoke(self, data: Layer0Model, on_progress: Optional[Callable[[TransactionO1Sage], None]] = None):
        if on_progress is not None:
            on_progress(AwaitingQueue())

        async with GlobalDBLock.get():
            return await self._perform_transaction(data, on_progress)

    async def _perform_transaction(
        self, data: Layer0Model, on_progress: Optional[Callable[[TransactionO1Sage], None]]
    ) -> list[Layer1Model]:
        if on_progress is not None:
            models, fails = await self._transformation_use_case.invoke(
                data, lambda stage: on_progress(TransformingData(stage))
            )
        else:
            models, fails = await self._transformation_use_case.invoke(data)
        # process fails by user interaction
        for _, fail in fails.iterrows():
            if isinstance(fail["cause"], CrossIdentificationException):
                # TODO implement
                pass
            elif isinstance(fail["cause"], ValueError):
                # error parsing coordinates
                res: ResolveCoordinateParseFailRes = await self._resolve_coordinate_parse_fail.eval(
                    ResolveCoordinateParseFailArg(fail["cause"])
                )
                # process user action
                if not res.is_cancelled:
                    raise fail["cause"]

        updated_source, updated_models = self._update_update_time(data, models)
        await self._write_transformed_data_to_db(updated_models)
        await self._write_transformed_source_to_db(updated_source)

        return updated_models

    def _update_update_time(
        self, source: Layer0Model, models: list[Layer1Model]
    ) -> tuple[Layer0Model, list[Layer1Model]]:
        """
        Update info about data frame last processing
        :param source: Source of data, being transformed
        :param models: Successfully processed models
        :return: updated source and models
        """
        # TODO implement
        updated_source = replace(source, processed=True)
        return updated_source, models

    async def _write_transformed_data_to_db(self, models: list[Layer1Model]):
        await self._layer_1_repository.save_update_instances(models)

    async def _write_transformed_source_to_db(self, source: Layer0Model):
        await self._layer_0_repository.create_update_instances([source])
