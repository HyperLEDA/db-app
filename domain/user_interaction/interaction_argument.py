from abc import ABC

from domain.usecases.exceptions import CrossIdentificationException


class AbstractArgument(ABC):
    pass


class ResolveCrossIdentificationCollisionInteractionArg(AbstractArgument):
    def __init__(self, cross_identification_fail: CrossIdentificationException):
        self.cross_Identification_fail: CrossIdentificationException = cross_identification_fail


class ResolveCoordinateParseFailArg(AbstractArgument):
    def __init__(self, cause: ValueError):
        self.cause: ValueError = cause


class Confirm01TransactionArg(AbstractArgument):
    def __init__(self):
        pass
