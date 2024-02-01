from dataclasses import dataclass


@dataclass
class Transaction01Fail:
    cause: BaseException
