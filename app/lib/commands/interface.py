import abc


class Command(abc.ABC):
    """
    Base class for any command that can be run by the CLI.
    """

    @classmethod
    def help(cls) -> str:
        """
        Return a string that describes the command.
        """
        return cls.__doc__ or ""

    @abc.abstractmethod
    def prepare(self):
        """
        `prepare` is executed before anything else. It should be used to
        initialize any resources that the command will need, including database connections,
        clients, etc.
        """

    @abc.abstractmethod
    def run(self):
        """
        `run` is the business logic of the command.
        """

    @abc.abstractmethod
    def cleanup(self):
        """
        `cleanup` is executed after the command has finished running.
        It should be used to destroy any resources that were initialized in `prepare`.

        This method is guaranteed to be called, even if an exception is raised during `prepare` or `run`.
        """
