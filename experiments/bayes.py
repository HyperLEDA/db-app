import sys
from pathlib import Path

import numpy as np
from astropy import coordinates
from astropy import units as u

sys.path.insert(0, str(Path(__file__).parent / ".."))

import math

import pandas
import structlog

from app.data import model
from app.data.repositories.layer2 import filters, params
from app.data.repositories.layer2.repository import Layer2Repository
from experiments.entities import CrossIdentificationResult

logger = structlog.get_logger()


def calculate_bayes_factor(ra1: float, dec1: float, sigma1: float, ra2: float, dec2: float, sigma2: float) -> float:
    """
    Calculate the Bayes factor for two observations.

    Args:
        ra1, dec1: Coordinates of first observation (degrees)
        sigma1: Astrometric error of first observation (degrees)
        ra2, dec2: Coordinates of second observation (degrees)
        sigma2: Astrometric error of second observation (degrees)

    Returns:
        Bayes factor B(H,K|D)
    """
    c1 = coordinates.SkyCoord(ra1 * u.deg, dec1 * u.deg, frame="icrs")
    c2 = coordinates.SkyCoord(ra2 * u.deg, dec2 * u.deg, frame="icrs")
    sep = c1.separation(c2).to(u.rad).value

    sigma1_rad = math.radians(sigma1)
    sigma2_rad = math.radians(sigma2)

    return 2 / (sigma1_rad**2 + sigma2_rad**2) * math.exp(-(sep**2) / (2.0 * (sigma1_rad**2 + sigma2_rad**2)))


def bayes_to_posterior(bayes_factor: float, prior: float) -> float:
    if bayes_factor <= 0:
        return 0

    return (1.0 + (1.0 - prior) / (bayes_factor * prior)) ** -1


def posterior_to_bayes(posterior: float, prior: float) -> float:
    assert posterior >= 0 and posterior <= 1

    return (posterior * (1.0 - prior)) / (prior * (1.0 - posterior))


def cross_identify_objects_bayesian(
    parameters: pandas.DataFrame,
    layer2_repo: Layer2Repository,
    lower_posterior_probability: float,
    upper_posterior_probability: float,
    cutoff_radius_degrees: float,
    prior_probability: float,
) -> dict[str, CrossIdentificationResult]:
    """
    Perform cross-identification using Bayesian approach.

    Args:
        positions: DataFrame, containing "ra", "dec" and "e_pos" columns.
        layer2_repo: Layer2Repository instance for database queries
        lower_posterior_probability: Threshold for "definitely different"
        upper_posterior_probability: Threshold for "definitely same"
        cutoff_radius_degrees: Search radius in degrees
        prior_probability: Prior probability that two random objects are the same

    Returns:
        Dictionary mapping object IDs to cross-identification results
    """
    results: dict[str, CrossIdentificationResult] = {}

    ra_column = parameters["ra"]
    dec_column = parameters["dec"]
    error_column = parameters["e_pos"]

    bf_lower = posterior_to_bayes(lower_posterior_probability, prior_probability)
    bf_upper = posterior_to_bayes(upper_posterior_probability, prior_probability)

    logger.info("Bayes factors", b_lower=bf_lower, b_upper=bf_upper)

    batch_size = 50
    total_objects = len(ra_column)

    for batch_start in range(0, total_objects, batch_size):
        batch_end = min(batch_start + batch_size, total_objects)

        logger.info("Processing batch", batch_n=batch_start // batch_size + 1, start=batch_start + 1, end=batch_end)

        search_types: dict[str, filters.Filter] = {"icrs": filters.ICRSCoordinatesInRadiusFilter(cutoff_radius_degrees)}

        search_params = {}
        for i in range(batch_start, batch_end):
            object_id = f"obj_{i}"
            search_params[object_id] = params.ICRSSearchParams(ra=ra_column[i], dec=dec_column[i])

        batch_results = layer2_repo.query_batch(
            catalogs=[model.RawCatalog.ICRS],
            search_types=search_types,
            search_params=search_params,
            limit=10000,
            offset=0,
        )

        for i in range(batch_start, batch_end):
            object_id = f"obj_{i}"
            candidates = batch_results.get(object_id, [])

            if len(candidates) == 0:
                results[object_id] = CrossIdentificationResult(status="new")
                continue

            candidate_pgcs = []

            for candidate in candidates:
                icrs_data: model.ICRSCatalogObject | None = None
                for catalog_obj in candidate.data:
                    if isinstance(catalog_obj, model.ICRSCatalogObject):
                        icrs_data = catalog_obj
                        break

                if icrs_data is None:
                    continue

                bf = calculate_bayes_factor(
                    ra_column[i],
                    dec_column[i],
                    error_column[i],
                    icrs_data.ra,
                    icrs_data.dec,
                    np.sqrt(icrs_data.e_ra**2 + icrs_data.e_dec**2),
                )

                candidate_pgcs.append((candidate.pgc, bf))

            high_probability_matches = [
                (pgc, bayes_to_posterior(bf, prior_probability)) for pgc, bf in candidate_pgcs if bf > bf_upper
            ]
            low_probability_matches = [
                (pgc, bayes_to_posterior(bf, prior_probability)) for pgc, bf in candidate_pgcs if bf < bf_lower
            ]
            all_matches = [(pgc, bayes_to_posterior(bf, prior_probability)) for pgc, bf in candidate_pgcs]

            if len(high_probability_matches) == 1 and len(low_probability_matches) == len(candidate_pgcs) - 1:
                pgc, posterior = high_probability_matches[0]
                results[object_id] = CrossIdentificationResult(status="existing", pgc_numbers={pgc: posterior})
            elif len(low_probability_matches) == len(all_matches):
                results[object_id] = CrossIdentificationResult(status="new")
            else:
                results[object_id] = CrossIdentificationResult(status="collision", pgc_numbers=dict(all_matches))

    return results
