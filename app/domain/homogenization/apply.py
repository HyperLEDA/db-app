from collections.abc import Callable
from typing import Any

import structlog
from astropy import table

from app.data import model as data_model
from app.data import repositories
from app.domain.homogenization import model

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

Enricher = Callable[[Any], Any]


class Homogenization:
    def __init__(
        self,
        column_rules: dict[tuple[data_model.RawCatalog, str], dict[str, Any]],
        params_by_catalog: dict[tuple[data_model.RawCatalog, str], dict[str, Any]],
        ignore_errors: bool = True,
    ):
        self.column_rules = column_rules
        self.params_by_catalog = params_by_catalog
        self.ignore_errors = ignore_errors

    def apply(self, data: table.Table) -> list[data_model.Layer0Object]:
        catalog_objects: dict[tuple[data_model.RawCatalog, str], dict[str, table.Column]] = {}

        for key, params in self.column_rules.items():
            constructor_params = {}

            for param, col_name in params.items():
                constructor_params[param] = data[col_name]

            catalog_objects[key] = constructor_params

        for key, params in self.params_by_catalog.items():
            if key not in catalog_objects:
                catalog_objects[key] = {}

            for parameter, value in params.items():
                catalog_objects[key][parameter] = table.Column(data=[value] * len(data))  # type: ignore

        objects: dict[str, data_model.Layer0Object] = {}

        for (catalog, _), params_map in catalog_objects.items():
            ids = data[repositories.INTERNAL_ID_COLUMN_NAME]
            catalog_type = data_model.get_catalog_object_type(data_model.RawCatalog(catalog))

            for i in range(len(ids)):
                object_id = str(ids[i])
                if object_id not in objects:
                    objects[object_id] = data_model.Layer0Object(object_id, [])

                data_dict = {}
                for key in params_map:
                    data_dict[key] = params_map[key][i]
                    if (unit := params_map[key].unit) is not None:
                        data_dict[key] = data_dict[key] * unit

                try:
                    catalog_obj = catalog_type.from_custom(**data_dict)
                except Exception as e:
                    if not self.ignore_errors:
                        raise e

                    logger.warn("Error creating catalog object", object_id=object_id, error=e, data_dict=data_dict)
                    continue

                objects[object_id].data.append(catalog_obj)

        return [obj for obj in objects.values() if len(obj.data) > 0]


def get_homogenization(
    homogenization_rules: list[model.Rule],
    homogenization_params: list[model.Params],
    table_meta: data_model.Layer0TableMeta,
    **kwargs,
) -> Homogenization:
    rules_by_column: dict[str, list[model.Rule]] = {}

    for column in table_meta.column_descriptions:
        rules: dict[tuple[data_model.RawCatalog, str, str], model.Rule] = {}

        for rule in homogenization_rules:
            key = (rule.catalog, rule.parameter, rule.key)

            if rule.filter.apply(table_meta, column):
                rules[key] = rule

        if len(rules) == 0:
            continue

        if rules:
            rules_by_column[column.name] = list(rules.values())

    params_by_catalog: dict[tuple[data_model.RawCatalog, str], dict[str, Any]] = {}

    for param in homogenization_params:
        key = (param.catalog, param.key)

        if key not in params_by_catalog:
            params_by_catalog[key] = {}

        params_by_catalog[key].update(param.params)

    if len(rules_by_column) == 0:
        raise ValueError("No rules satisfy any of the table columns")

    priorities: dict[tuple[data_model.RawCatalog, str], dict[str, int]] = {}
    column_rules: dict[tuple[data_model.RawCatalog, str], dict[str, Any]] = {}

    for column_name, col_rules in rules_by_column.items():
        for rule in col_rules:
            key = (rule.catalog, rule.key)

            if key not in priorities:
                priorities[key] = {}
                column_rules[key] = {}

            if rule.parameter not in priorities[key] or rule.priority > priorities[key][rule.parameter]:
                priorities[key][rule.parameter] = rule.priority
                column_rules[key][rule.parameter] = column_name

    return Homogenization(column_rules, params_by_catalog, **kwargs)
