from dataclasses import dataclass, replace
from typing import Callable, Optional

from app.domain.actions.logic_units.transformation_0_1 import TransformationO1Depot, transformation_0_1
from app.domain.model import Layer0Model, Layer1Model
from app.domain.model.layer0 import Transformation01Fail
from app.domain.model.params.transaction_0_1_stages import (
    AwaitingQueue,
    TransactionO1Sage,
    TransformingData,
)


@dataclass
class Transaction01Depot:
    transformation_depot: TransformationO1Depot


def _perform_transaction(
    transformation_depot: TransformationO1Depot,
    data: Layer0Model,
    on_progress: Optional[Callable[[TransactionO1Sage], None]],
) -> tuple[Layer0Model, list[Layer1Model], list[Transformation01Fail]]:
    def fcn(*args, **kwargs):
        return transformation_0_1(transformation_depot, *args, **kwargs)

    if on_progress is not None:
        models, fails = fcn(data, lambda stage: on_progress(TransformingData(stage)))
    else:
        models, fails = fcn(data)

    updated_source, updated_models = _update_update_time(data, models)

    return updated_source, updated_models, fails


def _update_update_time(source: Layer0Model, models: list[Layer1Model]) -> tuple[Layer0Model, list[Layer1Model]]:
    """
    Update info about data frame last processing
    :param source: Source of data, being transformed
    :param models: Successfully processed models
    :return: updated source and models
    """
    updated_source = replace(source, processed=True)
    return updated_source, models


def transaction_0_1(
    depot: Transaction01Depot, data: Layer0Model, on_progress: Optional[Callable[[TransactionO1Sage], None]] = None
) -> tuple[Layer0Model, list[Layer1Model], list[Transformation01Fail]]:
    """
    Performs data transaction from layer 0 to layer 1
    :param depot: Dependencies
    :param data: Layer 0 data to be transformed
        :param on_progress: Function, called on pogress
        :return:
            updated_source: Updated Layer 0 data (according to transformation result)
            updated_models: Successfully transformed Layer 1 data
            fails: Fails during transformation
    """
    if on_progress is not None:
        on_progress(AwaitingQueue())

    return _perform_transaction(depot.transformation_depot, data, on_progress)
