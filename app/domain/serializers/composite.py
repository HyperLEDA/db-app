from concurrent import futures

from app import entities
from app.data import repositories
from app.domain.serializers import interface


class CompositeSerializer(interface.Layer1Serializer):
    def __init__(self, *serializers: interface.Layer1Serializer) -> None:
        self._serializers = serializers

    def serialize(self, repo: repositories.Layer1Repository, objects: list[entities.ObjectProcessingInfo]) -> None:
        threads = []
        with futures.ThreadPoolExecutor() as group:
            for serializer in self._serializers:
                threads.append(group.submit(serializer.serialize, repo, objects))

        for thread in threads:
            thread.result()
