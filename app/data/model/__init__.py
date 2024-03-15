from dataclasses import dataclass


@dataclass
class Bibliography:
    bibcode: str
    year: int
    author: list[str]
    title: str
