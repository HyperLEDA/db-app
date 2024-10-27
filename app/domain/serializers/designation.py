from app import entities
from app.data import model, repositories
from app.domain.serializers import interface


class DesignationSerializer(interface.Layer1Serializer):
    def serialize(self, repo: repositories.Layer1Repository, objects: list[entities.ObjectProcessingInfo]) -> None:
        layer1_objects = []

        for obj in objects:
            layer1_objects.append(object_info_to_layer1_data(obj))

        repo.save_data(model.Layer1Catalog.DESIGNATION, layer1_objects)


def object_info_to_layer1_data(obj: entities.ObjectProcessingInfo) -> model.Layer1CatalogObject:
    if obj.pgc is None:
        raise ValueError("PGC is required to transfer to layer 1")

    return model.Layer1CatalogObject(
        pgc=obj.pgc,
        object_id=obj.object_id,
        data={"design": obj.data.primary_name},
    )
