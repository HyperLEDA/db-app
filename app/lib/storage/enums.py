import enum


class DataType(enum.Enum):
    REGULAR = "regular"
    REPROCESSING = "reprocessing"
    PRELIMINARY = "preliminary"
    COMPILATION = "compilation"


class RecordCrossmatchStatus(str, enum.Enum):
    UNPROCESSED = "unprocessed"
    NEW = "new"
    COLLIDED = "collided"
    EXISTING = "existing"


class Nature(enum.Enum):
    STAR = "*"
    STAR_SYSTEM = "*S"
    INTERSTELLAR_MEDIUM = "ISM"
    GALAXY = "G"
    MULTIPLE_GALAXIES = "MG"
    OTHER = "O"
    ERROR = "X"
