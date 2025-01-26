from collections.abc import Callable

from app import entities
from app.domain.cross_id_simultaneous_data_provider import CrossIdSimultaneousDataProvider
from app.domain.model import Layer0Model, Layer1Model
from app.domain.model.layer0 import Transformation01Fail
from app.domain.model.layer1.layer_1_value import Layer1Value
from app.domain.model.params.cross_identification_result import CrossIdentifyResult
from app.domain.model.params.cross_identification_user_param import CrossIdentificationUserParam
from app.domain.model.params.transformation_0_1_stages import (
    CrossIdentification,
    ParseCoordinates,
    ParseValues,
    Transformation01Stage,
)
from app.domain.repositories.layer_2_repository import Layer2Repository


class TransformationO1UseCase:
    """
    Performs data transformation from layer 0 [Layer0Model] to layer 1 [Layer1Model]
    """

    def __init__(
        self,
        layer2_repo: Layer2Repository,
        cross_identification_function: Callable[
            [Layer2Repository, entities.ObjectInfo, CrossIdSimultaneousDataProvider, CrossIdentificationUserParam],
            CrossIdentifyResult,
        ],
        simultaneous_data_provider: Callable[[list[entities.ObjectInfo]], CrossIdSimultaneousDataProvider],
    ):
        """
        :param cross_identification_function: Cross identification logic
        :param simultaneous_data_provider: Function, used to obtain simultaneous data provider for cross identification
        """
        self._layer2_repo = layer2_repo
        self._cross_identification_function = cross_identification_function
        self._simultaneous_data_provider = simultaneous_data_provider

    def with_mocked_cross_identification(
        self,
        layer2_repo: Layer2Repository,
        cross_identification_function: Callable[
            [Layer2Repository, entities.ObjectInfo, CrossIdSimultaneousDataProvider, CrossIdentificationUserParam],
            CrossIdentifyResult,
        ],
    ):
        return TransformationO1UseCase(layer2_repo, cross_identification_function, self._simultaneous_data_provider)

    async def invoke(
        self,
        data: Layer0Model,
        user_param: CrossIdentificationUserParam | None = None,
        on_progress: Callable[[Transformation01Stage], None] | None = None,
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
        if data.meta.names_descr is not None:
            names = data.meta.names_descr.parse_name(data.data)
        else:
            names = n_rows * [None]

        # cross identification
        identification_params = []
        for coordinate, name in zip(coordinates, names, strict=False):
            if isinstance(coordinate, BaseException):
                identification_params.append(coordinate)
            elif isinstance(name, BaseException):
                identification_params.append(name)
            elif name is None:
                identification_params.append(entities.ObjectInfo(None, None, coordinate))
            else:
                primary_name, all_names = name
                identification_params.append(entities.ObjectInfo(all_names, primary_name, coordinate))
        # Simultaneous data provider needs only valid entities.ObjectInfos
        simultaneous_data_provider = self._simultaneous_data_provider(
            [it for it in identification_params if not isinstance(it, BaseException)]
        )
        identification_results = []
        for i, param in enumerate(identification_params):
            if isinstance(param, BaseException):
                identification_results.append(param)
            else:
                identification_results.append(
                    self._cross_identification_function(
                        self._layer2_repo,
                        param,
                        simultaneous_data_provider,
                        user_param,
                    )
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

            if identification_result.fail is not None:
                fails.append(Transformation01Fail(identification_result.fail, i))
                continue

            pgc = identification_result.result.pgc if identification_result.result is not None else None
            model = Layer1Model(
                pgc=pgc,
                source_id=data.id,
                processed=False,
                coordinates=coordinate,
                name=names[i],
                measurements=[
                    Layer1Value(value[i], data.meta.value_descriptions[i_descr].ucd)
                    for i_descr, value in enumerate(values)
                ],
                dataset=data.meta.dataset,
            )
            models.append(model)

        return models, fails
