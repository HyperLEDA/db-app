from dataclasses import dataclass


@dataclass
class PreliminaryNew:
    pass


@dataclass
class PreliminaryExisting:
    pgc: int


@dataclass
class PreliminaryColliding:
    pgcs: set[int]


PreliminaryStatus = PreliminaryNew | PreliminaryExisting | PreliminaryColliding
