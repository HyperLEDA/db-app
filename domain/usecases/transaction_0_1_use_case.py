from typing import Callable, Optional

from . import CrossIdentifyUseCase
from ..model import Layer0Model
from ..model.transformation_0_1_stages import Transformation01Stage
from ..util import GlobalDBLock


class Transaction01UseCase:
    """
    Performs data transaction from layer 0 to layer 1
    """
    def __init__(self, cross_identify_use_case: CrossIdentifyUseCase):
        self._cross_identify_use_case: CrossIdentifyUseCase = cross_identify_use_case

    async def invoke(
            self,
            data: Layer0Model,
            on_progress: Optional[Callable[[Transformation01Stage], None]] = None
    ):
        async with GlobalDBLock.get():
            pass
