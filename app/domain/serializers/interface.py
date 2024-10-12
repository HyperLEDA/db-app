import abc

from app import entities
from app.data import repositories


class Layer1Serializer(abc.ABC):
    """
    Base class for storing objects to Layer 1.

    Incapsulates the knowledge of the tables on layer 1 and stores the data inside tables
    that are relevant to that specific catalogue.
    """

    def serialize(self, repo: repositories.Layer1Repository, objects: list[entities.ObjectInfo]):
        """
        Saves a batch of objects inside the tables on layer 1.

        Does not guarantee that all of the properties of the objects will be saved.

        If relevant properties are missing, raises `SerializerNotEnoughInfoError`
        """
