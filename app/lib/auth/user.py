import enum
from dataclasses import dataclass


class Role(enum.Enum):
    ADMIN = "admin"


@dataclass
class User:
    user_id: str
    role: Role
