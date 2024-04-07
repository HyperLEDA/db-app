from dataclasses import dataclass


@dataclass
class Transformation01Fail:
    """
    Holds information about a fail and it's cause
    Args:
        cause: Fail cause
        original_row: Row in original table
    """
    cause: BaseException
    original_row: int
