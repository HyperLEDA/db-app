import numpy as np
import psycopg
from astropy import units as u

from app.data import model
from app.data.repositories import layer1
from app.lib.web.errors import RuleValidationError
from app.presentation import adminapi


class Layer1Writer:
    def __init__(self, layer1_repo: layer1.Layer1Repository) -> None:
        self._layer1_repo = layer1_repo

    def save_data(self, request: adminapi.SaveStructuredDataRequest) -> adminapi.SaveStructuredDataResponse:
        catalog = model.RawCatalog(request.catalog)
        object_cls = model.get_catalog_object_type(catalog)
        table = object_cls.layer1_table()

        internal_units = self._layer1_repo.get_column_units(catalog)
        missing = [col for col in request.columns if col in internal_units and col not in request.units]
        if missing:
            raise RuleValidationError(f"units required for columns: {', '.join(sorted(missing))}")

        factors = np.ones(len(request.columns))
        for j, col in enumerate(request.columns):
            if col in internal_units and col in request.units:
                factors[j] = (1.0 * u.Unit(request.units[col])).to(u.Unit(internal_units[col])).value

        data_arr = np.array(request.data)
        converted = (data_arr * factors).tolist()

        try:
            self._layer1_repo.save_structured_data(table, request.columns, request.ids, converted)
        except psycopg.errors.ForeignKeyViolation as e:
            raise RuleValidationError("one or more record ids do not exist in layer0.records") from e

        return adminapi.SaveStructuredDataResponse()
