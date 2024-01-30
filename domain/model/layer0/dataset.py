from dataclasses import dataclass


@dataclass
class Dataset:
    """
    Describes where data came from, measurements specifics
    Args:
        reliability: A string from enum [domain.model.constants.Reliability], used to determine reliability og the data
    """
    reliability: str
