from dataclasses import dataclass


@dataclass
class Bibliography:
    id: int
    bibcode: str
    year: int
    author: list[str]
    title: str
