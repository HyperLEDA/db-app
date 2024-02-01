from typing import Optional
from dataclasses import dataclass


@dataclass
class ColumnNotFoundException(RuntimeError):
    """
    Thrown when parser form metadata can not find column
    """
    column_names: list[str]
    cause: Optional[BaseException] = None
    message: Optional[str] = None
