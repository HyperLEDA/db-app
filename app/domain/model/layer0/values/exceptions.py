from dataclasses import dataclass


@dataclass
class ColumnNotFoundException(RuntimeError):
    """
    Thrown when parser form metadata can not find column
    """

    column_names: list[str]
    cause: BaseException | None = None
    message: str | None = None
