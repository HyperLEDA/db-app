from app.data import repositories
from app.domain.model import Layer0Model
from app.domain.util import GlobalDBLock


class StoreL0UseCase:
    """
    Stores data of layer 0. Throws error if repository fails to perform operation
    """

    def __init__(self, repository: repositories.Layer0Repository):
        self._repository: repositories.Layer0Repository = repository

    async def invoke(self, instances: list[Layer0Model]):
        async with GlobalDBLock.get():
            await self._repository.create_instances(instances)
