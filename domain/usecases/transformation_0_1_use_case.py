from typing import Callable, Optional
import uuid

import pandas as pd
from pandas import DataFrame

from ..model import Layer0Model, Layer1Model
from ..model.layer0.values.exceptions import ColumnNotFoundException
from .cross_identify_use_case import CrossIdentifyUseCase
from ..model.params.cross_identification_param import CrossIdentificationParam
from domain.model.params.transformation_0_1_stages import Transformation01Stage, ParseCoordinates, ParseValues, CrossIdentification


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
    ) -> tuple[list[Layer1Model], DataFrame]:
        """
        :param data: Layer 0 data to be transformed
        :param on_progress: Optional callable to call on progress (from 0.0 to 1.0)
        :return:
            success: list[Layer1Model] - transformed models
            fail: DataFrame - Rows from original data, that failed, with additional 'cause' column, holding exception,
            describing the fail
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
            if isinstance(coordinate, BaseException):
                # case, where there was an error parsing coordinates, we still can make cross identification
                cross_id_data = CrossIdentificationParam(name, None)
            else:
                cross_id_data = CrossIdentificationParam(name, coordinate)
            obj_ids.append(await self._cross_identify_use_case.invoke(cross_id_data))
            if on_progress is not None:
                on_progress(CrossIdentification(n_rows, i+1))

        # compile objects
        models = []
        fails = pd.DataFrame(columns=data.data.columns.to_list() + ['cause'])
        for i in range(0, n_rows):
            coordinate, obj_id = (coordinates[i], obj_ids[i])
            if isinstance(coordinate, BaseException):
                new_row = pd.concat([data.data.iloc[i], pd.Series({'cause': coordinate})])
                fails.loc[len(fails.index)] = new_row
                continue

            if isinstance(obj_id, BaseException):
                new_row = pd.concat([data.data.iloc[i], pd.Series({'cause': obj_id})])
                fails.loc[len(fails.index)] = new_row
                continue

            model = Layer1Model(
                id=uuid.uuid4().int,
                objectId=obj_id,
                sourceId=data.id,
                processed=False,
                coordinates=coordinate,
                name=names[i],
                measurements=[value[i] for value in values],
                dataset=data.meta.dataset
            )
            models.append(model)

        return models, fails
