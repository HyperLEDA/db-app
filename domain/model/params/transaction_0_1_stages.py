from abc import ABC
from dataclasses import dataclass

from domain.model.params.transformation_0_1_stages import Transformation01Stage


class TransactionO1Sage(ABC):
    pass


@dataclass
class AwaitingQueue(TransactionO1Sage):
    pass


@dataclass
class TransformingData(TransactionO1Sage):
    stage: Transformation01Stage


@dataclass
class AwaitingDecision(TransactionO1Sage):
    pass
