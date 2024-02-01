from typing import Optional
from astropy.coordinates import SkyCoord


class CrossIdentifyUseCase:
    """
    Finds an object by name or coordinates and return's it's id, or creates a new id, if it's a new object
    """
    async def invoke(self, name: Optional[str], coordinates: Optional[SkyCoord]) -> int:
        """
        :param name: Well known name of the object
        :param coordinates: Sky coordinates of the object
        :return: id for this object
        """
        # TODO implement
        pass
