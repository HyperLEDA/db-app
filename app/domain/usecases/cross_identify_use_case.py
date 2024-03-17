from app.domain.model.params.cross_identification_param import CrossIdentificationParam
from app.domain.usecases.exceptions import CrossIdentificationException


class CrossIdentifyUseCase:
    """
    Finds an object by name or coordinates and return's it's id, or creates a new id, if it's a new object.
    If there is a collision, returns this collision description
    """

    async def invoke(self, param: CrossIdentificationParam) -> int | CrossIdentificationException:
        """
        :param param: Data, used to identify object
        :return: id for this object
        """
        # TODO implement
        return 0
