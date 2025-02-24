import abc


class Task(abc.ABC):
    """
    Represents an asynchronous task that performs some operation on data in the database.
    """

    @classmethod
    @abc.abstractmethod
    def name(cls):
        pass

    @abc.abstractmethod
    def prepare(self, config_path: str):
        pass

    @abc.abstractmethod
    def run(self):
        pass

    @abc.abstractmethod
    def cleanup(self):
        pass
