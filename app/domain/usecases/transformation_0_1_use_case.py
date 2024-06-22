from typing import Callable, Optional

from app.domain.cross_id_simultaneous_data_provider import CrossIdSimultaneousDataProvider
from app.domain.model import Layer0Model, Layer1Model
from app.domain.model.layer0 import Transformation01Fail
from app.domain.model.layer0.values.exceptions import ColumnNotFoundException
from app.domain.model.params.cross_dentification_user_param import CrossIdentificationUserParam
from app.domain.model.params.cross_identification_param import CrossIdentificationParam
from app.domain.model.params.transformation_0_1_stages import (
    CrossIdentification,
    ParseCoordinates,
    ParseValues,
    Transformation01Stage,
)
from app.domain.usecases.cross_identify_use_case import CrossIdentifyUseCase


class TransformationO1UseCase:
    """
    Performs data transformation from layer 0 [Layer0Model] to layer 1 [Layer1Model]
    """

    def __init__(
        self,
        cross_identify_use_case: CrossIdentifyUseCase,
        simultaneous_data_provider: Callable[[list[CrossIdentificationParam]], CrossIdSimultaneousDataProvider],
    ):
        """
        :param cross_identify_use_case: Cross identification logic
        :param simultaneous_data_provider: Function, used to obtain simultaneous data provider for cross identification
        """
        self._cross_identify_use_case: CrossIdentifyUseCase = cross_identify_use_case
        self._simultaneous_data_provider = simultaneous_data_provider

    def with_mocked_cross_identify_use_case(self, new_use_case: CrossIdentifyUseCase):
        return TransformationO1UseCase(new_use_case, self._simultaneous_data_provider)

    async def invoke(
        self,
        data: Layer0Model,
        user_param: CrossIdentificationUserParam | None = None,
        on_progress: Optional[Callable[[Transformation01Stage], None]] = None,
    ) -> tuple[list[Layer1Model], list[Transformation01Fail]]:
        """
        :param data: Layer 0 data to be transformed
        :param user_param: User defined parameters for cross identification
        :param on_progress: Optional callable to call on progress (from 0.0 to 1.0)
        :return:
            success: list[Layer1Model] - transformed models
            fail: list[Transformation01Fail] - Fails during transformation
        """
        if user_param is None:
            user_param = CrossIdentificationUserParam(None, None)
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

        # extract names
        if data.meta.name_col is not None:
            names = data.data.get(data.meta.name_col)
            if names is None:
                raise ColumnNotFoundException([data.meta.name_col])
        else:
            names = n_rows * [None]

        # cross identification
        identification_params = []
        for coordinate, name in zip(coordinates, names):
            if isinstance(coordinate, BaseException):
                # case, where there was an error parsing coordinates, we still can make cross identification
                identification_params.append(CrossIdentificationParam(name, None))
            else:
                identification_params.append(CrossIdentificationParam(name, coordinate))
        simultaneous_data_provider = self._simultaneous_data_provider(identification_params)
        identification_results = []
        for i, param in zip(list(range(n_rows)), identification_params):
            identification_results.append(
                await self._cross_identify_use_case.invoke(param, simultaneous_data_provider, user_param)
            )
            if on_progress is not None:
                on_progress(CrossIdentification(n_rows, i + 1))
        simultaneous_data_provider.clear()

        # compile objects
        models = []
        fails = []
        for i in range(n_rows):
            coordinate, identification_result = (coordinates[i], identification_results[i])
            if isinstance(coordinate, BaseException):
                fails.append(Transformation01Fail(coordinate, i))
                continue

            if isinstance(identification_result, BaseException):
                fails.append(Transformation01Fail(identification_result, i))
                continue

            pgc = identification_result.result.pgc if identification_result.result is not None else None
            model = Layer1Model(
                pgc=pgc,
                source_id=data.id,
                processed=False,
                coordinates=coordinate,
                name=names[i],
                measurements=[value[i] for value in values],
                dataset=data.meta.dataset,
            )
            models.append(model)

        return models, fails
