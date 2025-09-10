from dataclasses import dataclass


@dataclass
class Bibliography:
    id: int
    code: str
    year: int
    author: list[str]
    title: str
