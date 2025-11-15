from collections.abc import Callable

from app.data import model

CIMatcher = Callable[[model.Record, model.Layer2Object], float]
CISolver = Callable[[list[tuple[model.Layer2Object, float]]], model.CIResult]
