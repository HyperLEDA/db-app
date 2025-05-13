from collections.abc import Callable
from typing import Any

import pandas
import structlog

from app.data import model as data_model
from app.data import repositories
from app.domain.homogenization import model

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

Enricher = Callable[[Any], Any]


class Homogenization:
    def __init__(
        self,
        rules_by_column: dict[str, list[model.Rule]],
        params_by_catalog: dict[tuple[str, str], dict[str, Any]],
        enricher_by_column: dict[str, Enricher],
        ignore_exceptions: bool = True,
    ):
        self.rules_by_column = rules_by_column
        self.params_by_catalog = params_by_catalog
        self.enricher_by_column = enricher_by_column
        self.ignore_exceptions = ignore_exceptions

    def apply(self, data: pandas.DataFrame) -> list[data_model.Layer0Object]:
        result: list[data_model.Layer0Object] = []

        for _, row in data.iterrows():
            priority_params: dict[tuple[data_model.RawCatalog, str], dict[str, tuple[Any, int]]] = {}
            for column_name in row.index:
                if column_name not in self.rules_by_column:
                    continue

                rules = self.rules_by_column[column_name]

                for rule in rules:
                    key = (rule.catalog, rule.key)

                    if key not in priority_params:
                        priority_params[key] = {}

                    if (
                        rule.parameter not in priority_params[key]
                        or rule.priority > priority_params[key][rule.parameter][1]
                    ):
                        value = row[column_name]
                        if column_name in self.enricher_by_column:
                            value = self.enricher_by_column[column_name](value)

                        priority_params[key][rule.parameter] = (value, rule.priority)

            catalog_objects: dict[tuple[data_model.RawCatalog, str], dict[str, Any]] = {}

            for key, params in priority_params.items():
                constructor_params = {}

                for param, (value, _) in params.items():
                    constructor_params[param] = value

                catalog_objects[key] = constructor_params

            for key in catalog_objects:
                if key not in self.params_by_catalog:
                    continue

                catalog_objects[key].update(self.params_by_catalog[key])

            obj = data_model.Layer0Object(row[repositories.INTERNAL_ID_COLUMN_NAME], [])

            for (catalog, _), data_dict in catalog_objects.items():
                catalog_type = data_model.get_catalog_object_type(data_model.RawCatalog(catalog))

                try:
                    catalog_obj = catalog_type.from_custom(**data_dict)
                except Exception as e:
                    if not self.ignore_exceptions:
                        raise e

                    logger.debug(
                        "Error creating catalog object",
                        object_id=row[repositories.INTERNAL_ID_COLUMN_NAME],
                        error=e,
                        data_dict=data_dict,
                    )
                    continue

                obj.data.append(catalog_obj)

            if len(obj.data) > 0:
                result.append(obj)

        return result


def get_homogenization(
    homogenization_rules: list[model.Rule],
    homogenization_params: list[model.Params],
    table_meta: data_model.Layer0TableMeta,
) -> Homogenization:
    rules_by_column: dict[str, list[model.Rule]] = {}
    enricher_by_column: dict[str, Enricher] = {}

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
            if column.unit is not None:
                enricher_by_column[column.name] = lambda v, u=column.unit: data_model.MeasuredValue(v, u)

    params_by_catalog: dict[tuple[data_model.RawCatalog, str], dict[str, Any]] = {}

    for param in homogenization_params:
        key = (param.catalog, param.key)

        if key not in params_by_catalog:
            params_by_catalog[key] = {}

        params_by_catalog[key].update(param.params)

    if len(rules_by_column) == 0:
        raise ValueError("No rules satisfy any of the table columns")

    return Homogenization(rules_by_column, params_by_catalog, enricher_by_column)
