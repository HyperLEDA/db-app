import dataclasses
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Add the parent directory to Python path so we can import from app
sys.path.insert(0, str(Path(__file__).parent / ".."))

import numpy as np
import pandas
import structlog

from app.data import model, repositories
from app.lib.storage import postgres
from experiments import entities
from experiments.bayes import cross_identify_objects_bayesian

logger = structlog.get_logger()
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)


def to_deg(arsec: float) -> float:
    return arsec / 3600


def get_objects(layer0_repo: repositories.Layer0Repository, table: str, cutoff: int) -> pandas.DataFrame:
    fashi_objects = layer0_repo.get_objects(table, cutoff, 0)
    icrs_objs: list[model.ICRSCatalogObject] = []
    name_objs: list[model.DesignationCatalogObject] = []
    for obj in fashi_objects:
        icrs_data = obj.get(model.ICRSCatalogObject)
        if icrs_data is not None:
            icrs_objs.append(icrs_data)

        name_data = obj.get(model.DesignationCatalogObject)
        if name_data is not None:
            name_objs.append(name_data)

    parameters = pandas.DataFrame()
    parameters["ra"] = [o.ra for o in icrs_objs]
    parameters["dec"] = [o.dec for o in icrs_objs]
    parameters["e_pos"] = [o.e_ra for o in icrs_objs]
    parameters["name"] = [o.designation for o in name_objs]

    return parameters


@dataclass
class Metrics:
    total_objects: int
    new_objects: int
    new_objects_ratio: float
    existing_objects: int
    existing_objects_ratio: float
    collision_objects: int
    collision_objects_ratio: float


def get_metrics(ci_results: dict[str, entities.CrossIdentificationResult]) -> Metrics:
    new_count = sum(1 for r in ci_results.values() if r.status == "new")
    existing_count = sum(1 for r in ci_results.values() if r.status == "existing")
    collision_count = sum(1 for r in ci_results.values() if r.status == "collision")
    total_count = len(ci_results)

    return Metrics(
        total_objects=total_count,
        new_objects=new_count,
        new_objects_ratio=new_count / total_count,
        existing_objects=existing_count,
        existing_objects_ratio=existing_count / total_count,
        collision_objects=collision_count,
        collision_objects_ratio=collision_count / total_count,
    )


@dataclass
class Hyperparameters:
    catalog: str
    cutoff: int
    lower_posterior: float
    upper_posterior: float
    cutoff_radius_arcsec: float
    # estimate of a probability for a random object to correspond to
    # a LEDA object within 100 arcsec from it
    prior: float


def main():
    storage_config = postgres.PgStorageConfig(
        endpoint="dm2.sao.ru", port=5432, dbname="hyperleda", user="hyperleda", password=os.getenv("DB_PASS") or ""
    )

    storage = postgres.PgStorage(storage_config, logger)
    storage.connect()

    layer0_repo = repositories.Layer0Repository(storage, logger)
    layer2_repo = repositories.Layer2Repository(storage, logger)

    results = pandas.DataFrame({})

    try:
        params_all = []
        metrics_all = []

        for prior in np.logspace(np.log10(0.01), np.log10(1), 20, endpoint=False):
            params = Hyperparameters(
                catalog="alfalfa_catalog",
                cutoff=500,
                lower_posterior=0.01,
                upper_posterior=0.99,
                cutoff_radius_arcsec=150,
                prior=prior,
            )
            params_all.append(params)

            results_bayesian = cross_identify_objects_bayesian(
                get_objects(layer0_repo, params.catalog, params.cutoff),
                layer2_repo,
                lower_posterior_probability=params.lower_posterior,
                upper_posterior_probability=params.upper_posterior,
                cutoff_radius_degrees=to_deg(params.cutoff_radius_arcsec),
                prior_probability=params.prior,
            )

            metrics_all.append(get_metrics(results_bayesian))
    except Exception as e:
        logger.error(f"Error during cross-identification: {e}")
        raise
    finally:
        storage.disconnect()

    for i, (params, metrics) in enumerate(zip(params_all, metrics_all, strict=False)):
        curr_results = {}
        curr_results.update(dataclasses.asdict(params))
        curr_results.update(dataclasses.asdict(metrics))

        print(curr_results)
        results = pandas.concat([results, pandas.DataFrame(curr_results, index=[i])], ignore_index=True)

    results.to_csv("experiments/data/results.csv")

    # print()
    # print("Bayesian:")
    # print_cross_identification_summary(results_bayesian)

    # save_cross_identification_results(
    #     results_bayesian, parameters, f"experiments/results/bayes_{cutoff_radius_arcsec}arcsec.csv"
    # )

    # print("Testing single-radius algorithm...")
    # search_radius_degrees = to_deg(20)
    # results_single = cross_identify_objects(fast_objects, layer2_repo, search_radius_degrees)

    # print("\nTesting two-radius algorithm...")
    # inner_radius_degrees = to_deg(10)
    # outer_radius_degrees = to_deg(20)
    # results_two_radius = cross_identify_objects_two_radius(
    #     fast_objects, layer2_repo, inner_radius_degrees, outer_radius_degrees
    # )

    # print()
    # print("Single radius:")
    # print_cross_identification_summary(results_single)

    # save_cross_identification_results(results_single, fast_objects, "experiments/results/single_radius.csv")

    # print()
    # print("Two-radius:")
    # print_cross_identification_summary(results_two_radius)

    # save_cross_identification_results(results_two_radius, fast_objects, "experiments/results/two_radius.csv")


if __name__ == "__main__":
    main()
