from typing import Callable, Optional
import uuid

from ..model import Layer0Model, Layer1Model
from ..model.layer0.values.exceptions import ColumnNotFoundException
from ..model.params import Transaction01Fail
from .cross_identify_use_case import CrossIdentifyUseCase
from ..model.transformation_0_1_stages import Transformation01Stage, ParseCoordinates, ParseValues, CrossIdentification


class TransformationO1UseCase:
    """
    Performs data transformation from layer 0 [Layer0Model] to layer 1 [Layer1Model]
    """
    def __init__(self, cross_identify_use_case: CrossIdentifyUseCase):
        self._cross_identify_use_case: CrossIdentifyUseCase = cross_identify_use_case

    async def invoke(
            self,
            data: Layer0Model,
            on_progress: Optional[Callable[[Transformation01Stage], None]] = None
    ) -> tuple[list[Layer1Model], list[Transaction01Fail]]:
        """
        :param data: Layer 0 data to be transformed
        :param on_progress: Optional callable to call on progress (from 0.0 to 1.0)
        :return:
            success: list[Layer1Model] - transformed models
            fail: list[Transaction01Fail] - failed to transform
        """
        n_rows = data.data.shape[0]

        # parse coordinates
        if on_progress is not None:
            on_progress(ParseCoordinates())
        cd = data.meta.coordinate_descr
        if cd is not None:
            coordinates = cd.parse_coordinates(data.data)
        else:
            coordinates = n_rows * [None]

        # parse values
        if on_progress is not None:
            on_progress(ParseValues())
        values = [vd.parse_values(data.data) for vd in data.meta.value_descriptions]

        # cross identification
        if data.meta.nameCol is not None:
            names = data.data.get(data.meta.nameCol)
            if names is None:
                raise ColumnNotFoundException([data.meta.nameCol])
        else:
            names = n_rows * [None]
        obj_ids = []
        for i, coordinate, name in zip(list(range(0, n_rows)), coordinates, names):
            obj_ids.append(await self._cross_identify_use_case.invoke(name, coordinate))
            if on_progress is not None:
                on_progress(CrossIdentification(n_rows, i+1))

        # compile objects
        models = []
        fails = []
        for i in range(0, n_rows):
            model = Layer1Model(
                id=uuid.uuid4().int,
                objectId=obj_ids[i],
                sourceId=data.id,
                processed=False,
                coordinates=coordinates[i],
                name=names[i],
                measurements=[value[i] for value in values],
                dataset=data.meta.dataset
            )
            models.append(model)

        return models, fails
