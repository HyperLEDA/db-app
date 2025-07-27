import sys
from pathlib import Path

# Add the parent directory to Python path so we can import from app
sys.path.insert(0, str(Path(__file__).parent / ".."))

import math

import pandas
import structlog

from app.data import model
from app.data.repositories.layer2 import filters, params
from app.data.repositories.layer2.repository import Layer2Repository
from experiments.entities import CrossIdentificationResult

logger = structlog.get_logger()


def normalize_position_error(error_arcsec: float, object_id: str = "unknown") -> float:
    """
    Normalize position error, handling zero or very small values.

    Args:
        error_arcsec: Position error in arcseconds
        object_id: Object identifier for logging

    Returns:
        Normalized error in degrees
    """
    if error_arcsec <= 0 or error_arcsec < 0.001:
        default_error = 1.0
        return default_error / 3600.0
    return error_arcsec / 3600.0


def calculate_angular_distance(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """
    Calculate angular distance between two points on the celestial sphere.

    Args:
        ra1, dec1: Coordinates of first point (degrees)
        ra2, dec2: Coordinates of second point (degrees)

    Returns:
        Angular distance in degrees
    """
    # Convert to radians
    ra1_rad = math.radians(ra1)
    dec1_rad = math.radians(dec1)
    ra2_rad = math.radians(ra2)
    dec2_rad = math.radians(dec2)

    # Calculate angular distance using spherical trigonometry
    cos_distance = math.sin(dec1_rad) * math.sin(dec2_rad) + math.cos(dec1_rad) * math.cos(dec2_rad) * math.cos(
        ra1_rad - ra2_rad
    )

    # Handle numerical precision issues
    cos_distance = max(-1.0, min(1.0, cos_distance))

    distance_rad = math.acos(cos_distance)
    return math.degrees(distance_rad)


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
    psi = calculate_angular_distance(ra1, dec1, ra2, dec2)

    psi_rad = math.radians(psi)
    if sigma1 == 0:
        sigma1 = 1 / 3600
    if sigma2 == 0:
        sigma2 = 1 / 3600

    sigma1_rad = math.radians(sigma1)
    sigma2_rad = math.radians(sigma2)

    w1 = 1.0 / (sigma1_rad**2)
    w2 = 1.0 / (sigma2_rad**2)

    return (2.0 * w1 * w2 / (w1 + w2)) * math.exp(-(psi_rad**2) * w1 * w2 / (2.0 * (w1 + w2)))


def posterior_probability_from_bayes_factor(bayes_factor: float, prior_probability: float) -> float:
    """
    Convert Bayes factor to posterior probability.

    Args:
        bayes_factor: Bayes factor B(H,K|D)
        prior_probability: Prior probability P(H)

    Returns:
        Posterior probability P(H|D)
    """
    if bayes_factor <= 0:
        return 0.0

    return 1.0 / (1.0 + (1.0 - prior_probability) / (bayes_factor * prior_probability))


def bayes_factor_from_posterior_probability(posterior_probability: float, prior_probability: float) -> float:
    """
    Convert posterior probability to Bayes factor.

    Args:
        posterior_probability: Posterior probability P(H|D)
        prior_probability: Prior probability P(H)

    Returns:
        Bayes factor B(H,K|D)
    """
    if posterior_probability <= 0 or posterior_probability >= 1:
        return 0.0

    return (posterior_probability * (1.0 - prior_probability)) / (prior_probability * (1.0 - posterior_probability))


def cross_identify_objects_bayesian(
    fast_objects: pandas.DataFrame,
    layer2_repo: Layer2Repository,
    lower_posterior_probability: float = 0.1,
    upper_posterior_probability: float = 0.9,
    cutoff_radius_degrees: float = 0.1,
    prior_probability: float = 1e-7,  # Assuming ~10M objects in HyperLEDA
) -> dict[str, CrossIdentificationResult]:
    """
    Perform cross-identification using Bayesian approach.

    Algorithm:
    1. For each object, search within cutoff radius
    2. Calculate Bayes factor for each candidate match
    3. Convert to posterior probability
    4. Classify based on probability thresholds:
       - If all P(H|D) < lower_threshold → "new"
       - If exactly one P(H|D) > upper_threshold → "existing"
       - Otherwise → "collision"

    Args:
        fast_objects: DataFrame containing objects to cross-identify
        layer2_repo: Layer2Repository instance for database queries
        lower_posterior_probability: Threshold for "definitely different" (default: 0.1)
        upper_posterior_probability: Threshold for "definitely same" (default: 0.9)
        cutoff_radius_degrees: Search radius in degrees (default: 0.1)
        prior_probability: Prior probability that two random objects are the same

    Returns:
        Dictionary mapping object IDs to cross-identification results
    """
    results: dict[str, CrossIdentificationResult] = {}

    # Check if fast_objects has required columns and map them to standard names
    ra_column = None
    dec_column = None
    error_column = None

    # Try different possible column names for coordinates
    for ra_name in ["ra", "RAJ2000", "RA", "ra_deg"]:
        if ra_name in fast_objects.columns:
            ra_column = ra_name
            break

    for dec_name in ["dec", "DEJ2000", "DEC", "dec_deg"]:
        if dec_name in fast_objects.columns:
            dec_column = dec_name
            break

    # Try to find error column
    for error_name in ["ePos", "e_ra", "e_dec", "pos_err", "error"]:
        if error_name in fast_objects.columns:
            error_column = error_name
            break

    if ra_column is None or dec_column is None:
        available_columns = list(fast_objects.columns)
        raise ValueError(f"Could not find RA/Dec columns. Available columns: {available_columns}")

    logger.info(f"Using Bayesian approach with cutoff radius: {cutoff_radius_degrees:.6f}°")
    logger.info(f"Using columns: {ra_column} for RA, {dec_column} for Dec")
    if error_column:
        logger.info(f"Using column: {error_column} for position errors")
    else:
        logger.warning("No error column found, using default error of 0.1 arcseconds")

    # Calculate Bayes factor thresholds
    B_lower = bayes_factor_from_posterior_probability(lower_posterior_probability, prior_probability)
    B_upper = bayes_factor_from_posterior_probability(upper_posterior_probability, prior_probability)

    logger.info(f"Bayes factor thresholds: B_lower={B_lower:.2e}, B_upper={B_upper:.2e}")

    # Process objects in batches
    batch_size = 1000
    total_objects = len(fast_objects)

    for batch_start in range(0, total_objects, batch_size):
        batch_end = min(batch_start + batch_size, total_objects)
        batch_objects = fast_objects.iloc[batch_start:batch_end]

        logger.info(f"Processing batch {batch_start // batch_size + 1}, objects {batch_start + 1}-{batch_end}")

        # Query for candidates within cutoff radius
        search_types: dict[str, filters.Filter] = {"icrs": filters.ICRSCoordinatesInRadiusFilter(cutoff_radius_degrees)}

        search_params = {}
        for idx, (_, obj) in enumerate(batch_objects.iterrows()):
            object_id = f"obj_{batch_start + idx}"
            search_params[object_id] = params.ICRSSearchParams(ra=obj[ra_column], dec=obj[dec_column])

        # Query the database
        batch_results = layer2_repo.query_batch(
            catalogs=[model.RawCatalog.ICRS],
            search_types=search_types,
            search_params=search_params,
            limit=1000,
            offset=0,
        )

        # Process results for this batch
        for idx, (_, obj) in enumerate(batch_objects.iterrows()):
            object_id = f"obj_{batch_start + idx}"
            candidates = batch_results.get(object_id, [])

            if len(candidates) == 0:
                # No candidates found
                results[object_id] = CrossIdentificationResult(status="new")
            else:
                # Calculate Bayes factors for all candidates
                ra = obj[ra_column]
                dec = obj[dec_column]

                # Get error for this object
                if error_column:
                    raw_error = obj[error_column]
                    sigma = normalize_position_error(raw_error, object_id)
                else:
                    sigma = normalize_position_error(0.1, object_id)  # Default 0.1 arcseconds

                bayes_factors = []
                candidate_pgcs = []

                for candidate in candidates:
                    # Find the ICRS data in the candidate
                    icrs_data = None
                    for catalog_obj in candidate.data:
                        if catalog_obj.catalog() == model.RawCatalog.ICRS:
                            icrs_data = catalog_obj
                            break

                    if icrs_data is None:
                        continue

                    # Get database object error, handling zero/small errors
                    db_error = icrs_data.e_ra  # type: ignore
                    db_sigma = normalize_position_error(db_error, f"PGC{candidate.pgc}")

                    # Calculate Bayes factor
                    B = calculate_bayes_factor(
                        ra,
                        dec,
                        sigma,
                        icrs_data.ra,  # type: ignore
                        icrs_data.dec,  # type: ignore
                        db_sigma,
                    )

                    bayes_factors.append(B)
                    candidate_pgcs.append(candidate.pgc)

                # Classify based on Bayes factors
                high_probability_matches = [i for i, B in enumerate(bayes_factors) if B > B_upper]
                low_probability_matches = [i for i, B in enumerate(bayes_factors) if B < B_lower]

                if len(high_probability_matches) == 1 and len(low_probability_matches) == len(bayes_factors) - 1:
                    # Exactly one high-probability match
                    results[object_id] = CrossIdentificationResult(
                        status="existing", pgc_numbers=[candidate_pgcs[high_probability_matches[0]]]
                    )
                else:
                    # Collision: multiple high-probability matches or no clear winner
                    results[object_id] = CrossIdentificationResult(status="collision", pgc_numbers=candidate_pgcs)

    return results


def create_simulated_data(num_objects: int = 100) -> pandas.DataFrame:
    """
    Create simulated data for testing the Bayesian algorithm.

    Args:
        num_objects: Number of objects to create

    Returns:
        DataFrame with simulated coordinates and errors
    """
    import numpy as np

    # Generate random coordinates
    ra = np.random.uniform(0, 360, num_objects)
    dec = np.random.uniform(-90, 90, num_objects)

    # Generate random errors (0.1 to 1.0 arcseconds)
    e_pos = np.random.uniform(0.1, 1.0, num_objects)

    # Create some objects that are close to each other (simulating same object)
    for i in range(0, num_objects, 10):
        if i + 1 < num_objects:
            # Make every 10th object close to the next one
            ra[i + 1] = ra[i] + np.random.normal(0, 0.001)  # ~3.6 arcseconds
            dec[i + 1] = dec[i] + np.random.normal(0, 0.001)

    return pandas.DataFrame(
        {
            "RAJ2000": ra,
            "DEJ2000": dec,
            "ePos": e_pos,
            "FASHI": [f"2023000{i:05d}" for i in range(num_objects)],
            "Name": [f"J{ra[i]:06.2f}{dec[i]:+06.2f}" for i in range(num_objects)],
        }
    )


def test_bayesian_algorithm():
    """
    Test the Bayesian cross-identification algorithm with simulated data.
    """
    print("Testing Bayesian cross-identification algorithm...")

    # Create simulated data
    simulated_data = create_simulated_data(50)
    print(f"Created {len(simulated_data)} simulated objects")

    # Test Bayes factor calculation with realistic parameters
    print("\nTesting Bayes factor calculation...")

    # Test case 1: Very close objects (should be high Bayes factor)
    sigma1 = 0.1 / 3600.0  # 0.1 arcseconds in degrees
    sigma2 = 0.1 / 3600.0  # 0.1 arcseconds in degrees
    separation_arcsec = 0.1  # 0.1 arcseconds separation
    separation_deg = separation_arcsec / 3600.0

    B = calculate_bayes_factor(0.0, 0.0, sigma1, separation_deg, 0.0, sigma2)
    P_H = 1e-7
    P_H_D = posterior_probability_from_bayes_factor(B, P_H)
    print("Very close objects (0.1 arcsec separation, 0.1 arcsec errors):")
    print(f"  Bayes factor: {B:.2e}")
    print(f"  Posterior probability: {P_H_D:.6f}")
    print(f"  Classification: {'existing' if P_H_D > 0.9 else 'collision' if P_H_D > 0.1 else 'new'}")

    # Test case 2: Moderate separation
    separation_arcsec = 1.0  # 1 arcsecond separation
    separation_deg = separation_arcsec / 3600.0
    B = calculate_bayes_factor(0.0, 0.0, sigma1, separation_deg, 0.0, sigma2)
    P_H_D = posterior_probability_from_bayes_factor(B, P_H)
    print("\nModerate separation (1 arcsec separation, 0.1 arcsec errors):")
    print(f"  Bayes factor: {B:.2e}")
    print(f"  Posterior probability: {P_H_D:.6f}")
    print(f"  Classification: {'existing' if P_H_D > 0.9 else 'collision' if P_H_D > 0.1 else 'new'}")

    # Test case 3: Large separation
    separation_arcsec = 10.0  # 10 arcseconds separation
    separation_deg = separation_arcsec / 3600.0
    B = calculate_bayes_factor(0.0, 0.0, sigma1, separation_deg, 0.0, sigma2)
    P_H_D = posterior_probability_from_bayes_factor(B, P_H)
    print("\nLarge separation (10 arcsec separation, 0.1 arcsec errors):")
    print(f"  Bayes factor: {B:.2e}")
    print(f"  Posterior probability: {P_H_D:.6f}")
    print(f"  Classification: {'existing' if P_H_D > 0.9 else 'collision' if P_H_D > 0.1 else 'new'}")

    # Test case 4: Realistic errors and lenient thresholds
    print("\nTesting with realistic errors and lenient thresholds:")
    sigma1_realistic = 1.0 / 3600.0  # 1.0 arcseconds in degrees
    sigma2_realistic = 1.0 / 3600.0  # 1.0 arcseconds in degrees

    # Test different separations with realistic errors
    for separation_arcsec in [1.0, 5.0, 10.0, 20.0]:
        separation_deg = separation_arcsec / 3600.0
        B = calculate_bayes_factor(0.0, 0.0, sigma1_realistic, separation_deg, 0.0, sigma2_realistic)
        P_H_D = posterior_probability_from_bayes_factor(B, P_H)
        print(f"  {separation_arcsec:2.0f} arcsec separation: B={B:.2e}, P(H|D)={P_H_D:.6f}")
        print(f"    Classification (0.3,0.7): {'existing' if P_H_D > 0.7 else 'collision' if P_H_D > 0.3 else 'new'}")

    # Test with different parameters
    print("\nTesting with different probability thresholds...")
    test_params = [
        (0.05, 0.95, 0.01),  # Very strict
        (0.1, 0.9, 0.05),  # Moderate
        (0.2, 0.8, 0.1),  # Lenient
    ]

    for lower_p, upper_p, cutoff_r in test_params:
        print(f"\nParameters: lower_p={lower_p}, upper_p={upper_p}, cutoff_r={cutoff_r}")

        # This would normally use a real repository, but for testing we'll just show the parameters
        B_lower = bayes_factor_from_posterior_probability(lower_p, 1e-7)
        B_upper = bayes_factor_from_posterior_probability(upper_p, 1e-7)
        print(f"  Bayes factor thresholds: B_lower={B_lower:.2e}, B_upper={B_upper:.2e}")

        # Show what separations would give these Bayes factors
        if B_upper > 0:
            # For the upper threshold, what separation gives this Bayes factor?
            # B = (2*w1*w2/(w1+w2)) * exp(-psi^2 * w1*w2/(2*(w1+w2)))
            # ln(B) = ln(2*w1*w2/(w1+w2)) - psi^2 * w1*w2/(2*(w1+w2))
            # psi^2 = 2*(w1+w2)/(w1*w2) * (ln(2*w1*w2/(w1+w2)) - ln(B))
            sigma1_rad = math.radians(sigma1)  # Convert sigma1 to radians
            w1 = w2 = 1.0 / (sigma1_rad**2)
            w1_rad = w1
            w2_rad = w2
            B_term = 2.0 * w1_rad * w2_rad / (w1_rad + w2_rad)
            psi_squared = 2.0 * (w1_rad + w2_rad) / (w1_rad * w2_rad) * (math.log(B_term) - math.log(B_upper))
            if psi_squared > 0:
                psi_rad = math.sqrt(psi_squared)
                psi_deg = math.degrees(psi_rad)
                psi_arcsec = psi_deg * 3600.0
                print(f"  Upper threshold separation: {psi_arcsec:.2f} arcseconds")


def test_simulated_cross_identification():
    """
    Test the cross-identification process with simulated data and mock results.
    """
    print("\n" + "=" * 60)
    print("Testing Simulated Cross-Identification Process")
    print("=" * 60)

    # Create simulated data
    simulated_data = create_simulated_data(20)
    print(f"Created {len(simulated_data)} simulated objects")

    # Simulate cross-identification results for different algorithms
    print("\nSimulating cross-identification results...")

    # Mock results for comparison
    mock_results = {
        "single_radius": {"new": 8, "existing": 10, "collision": 2},
        "two_radius": {"new": 10, "existing": 8, "collision": 2},
        "bayesian": {"new": 12, "existing": 6, "collision": 2},
    }

    print("\nSimulated Results Summary:")
    print("-" * 40)
    for algorithm, results in mock_results.items():
        total = sum(results.values())
        print(f"{algorithm.replace('_', ' ').title()}:")
        print(f"  New: {results['new']} ({results['new'] / total * 100:.1f}%)")
        print(f"  Existing: {results['existing']} ({results['existing'] / total * 100:.1f}%)")
        print(f"  Collision: {results['collision']} ({results['collision'] / total * 100:.1f}%)")
        print()

    # Test specific scenarios
    print("Testing specific scenarios:")
    print("-" * 30)

    # Scenario 1: Very close objects (should be high Bayes factor)
    ra1, dec1, sigma1 = 0.0, 0.0, 0.001  # 3.6 arcseconds
    ra2, dec2, sigma2 = 0.001, 0.001, 0.001  # Very close
    B = calculate_bayes_factor(ra1, dec1, sigma1, ra2, dec2, sigma2)
    P_H_D = posterior_probability_from_bayes_factor(B, 1e-7)
    print("Scenario 1 - Very close objects (0.001° separation):")
    print(f"  Bayes factor: {B:.2e}")
    print(f"  Posterior probability: {P_H_D:.6f}")
    print(f"  Classification: {'existing' if P_H_D > 0.9 else 'collision' if P_H_D > 0.1 else 'new'}")

    # Scenario 2: Moderate separation
    ra2, dec2 = 0.01, 0.01  # 36 arcseconds
    B = calculate_bayes_factor(ra1, dec1, sigma1, ra2, dec2, sigma2)
    P_H_D = posterior_probability_from_bayes_factor(B, 1e-7)
    print("\nScenario 2 - Moderate separation (0.01° separation):")
    print(f"  Bayes factor: {B:.2e}")
    print(f"  Posterior probability: {P_H_D:.6f}")
    print(f"  Classification: {'existing' if P_H_D > 0.9 else 'collision' if P_H_D > 0.1 else 'new'}")

    # Scenario 3: Large separation
    ra2, dec2 = 0.1, 0.1  # 6 arcminutes
    B = calculate_bayes_factor(ra1, dec1, sigma1, ra2, dec2, sigma2)
    P_H_D = posterior_probability_from_bayes_factor(B, 1e-7)
    print("\nScenario 3 - Large separation (0.1° separation):")
    print(f"  Bayes factor: {B:.2e}")
    print(f"  Posterior probability: {P_H_D:.6f}")
    print(f"  Classification: {'existing' if P_H_D > 0.9 else 'collision' if P_H_D > 0.1 else 'new'}")


def debug_bayesian_results(
    fast_objects: pandas.DataFrame,
    results: dict[str, CrossIdentificationResult],
    layer2_repo: Layer2Repository,
    cutoff_radius_degrees: float,
    lower_posterior_probability: float,
    upper_posterior_probability: float,
    prior_probability: float = 1e-7,
    num_samples: int = 10,
) -> None:
    """
    Debug Bayesian cross-identification results by analyzing specific cases.

    Args:
        fast_objects: The input data
        results: Cross-identification results
        layer2_repo: Repository for database queries
        cutoff_radius_degrees: Cutoff radius used
        lower_posterior_probability: Lower probability threshold
        upper_posterior_probability: Upper probability threshold
        prior_probability: Prior probability used
        num_samples: Number of sample objects to analyze
    """
    print(f"\n{'=' * 60}")
    print("DEBUGGING BAYESIAN CROSS-IDENTIFICATION RESULTS")
    print(f"{'=' * 60}")

    # Calculate Bayes factor thresholds
    B_lower = bayes_factor_from_posterior_probability(lower_posterior_probability, prior_probability)
    B_upper = bayes_factor_from_posterior_probability(upper_posterior_probability, prior_probability)

    print("Parameters:")
    print(f"  Cutoff radius: {cutoff_radius_degrees:.6f}° ({cutoff_radius_degrees * 3600:.2f} arcsec)")
    print(f"  Lower posterior probability: {lower_posterior_probability}")
    print(f"  Upper posterior probability: {upper_posterior_probability}")
    print(f"  Prior probability: {prior_probability:.2e}")
    print(f"  Bayes factor thresholds: B_lower={B_lower:.2e}, B_upper={B_upper:.2e}")

    # Find coordinate columns
    ra_column = None
    dec_column = None
    error_column = None

    for ra_name in ["ra", "RAJ2000", "RA", "ra_deg"]:
        if ra_name in fast_objects.columns:
            ra_column = ra_name
            break

    for dec_name in ["dec", "DEJ2000", "DEC", "dec_deg"]:
        if dec_name in fast_objects.columns:
            dec_column = dec_name
            break

    for error_name in ["ePos", "e_ra", "e_dec", "pos_err", "error"]:
        if error_name in fast_objects.columns:
            error_column = error_name
            break

    if not ra_column or not dec_column:
        print("ERROR: Could not find coordinate columns")
        return

    # Analyze sample objects from each category
    categories = {"new": [], "existing": [], "collision": []}
    for obj_id, result in results.items():
        if len(categories[result.status]) < num_samples:
            categories[result.status].append(obj_id)

    print(f"\nSample analysis ({num_samples} objects per category):")

    for category, obj_ids in categories.items():
        print(f"\n{category.upper()} objects:")
        print("-" * 40)

        for obj_id in obj_ids:
            # Get object data
            batch_idx = int(obj_id.split("_")[1])
            obj = fast_objects.iloc[batch_idx]
            ra = obj[ra_column]
            dec = obj[dec_column]

            # Get error
            if error_column:
                raw_error = obj[error_column]
                sigma = normalize_position_error(raw_error, obj_id)
            else:
                sigma = normalize_position_error(0.1, obj_id)

            print(f"\n{obj_id}: RA={ra:.6f}°, Dec={dec:.6f}°, σ={sigma * 3600:.3f} arcsec")

            # Query for candidates
            search_types: dict[str, filters.Filter] = {
                "icrs": filters.ICRSCoordinatesInRadiusFilter(cutoff_radius_degrees)
            }
            search_params: dict[str, params.SearchParams] = {obj_id: params.ICRSSearchParams(ra=ra, dec=dec)}

            batch_results = layer2_repo.query_batch(
                catalogs=[model.RawCatalog.ICRS],
                search_types=search_types,
                search_params=search_params,
                limit=1000,
                offset=0,
            )

            candidates = batch_results.get(obj_id, [])
            print(f"  Found {len(candidates)} candidates within {cutoff_radius_degrees * 3600:.1f} arcsec")

            if len(candidates) > 0:
                # Calculate Bayes factors for top candidates
                bayes_factors = []
                candidate_info = []

                for candidate in candidates[:5]:  # Show top 5
                    icrs_data = None
                    for catalog_obj in candidate.data:
                        if catalog_obj.catalog() == model.RawCatalog.ICRS:
                            icrs_data = catalog_obj
                            break

                    if icrs_data is None:
                        continue

                        # Calculate angular distance
                    psi = calculate_angular_distance(ra, dec, icrs_data.ra, icrs_data.dec)  # type: ignore

                    # Get database error
                    db_error = icrs_data.e_ra  # type: ignore
                    db_sigma = normalize_position_error(db_error, f"PGC{candidate.pgc}")

                    # Calculate Bayes factor
                    B = calculate_bayes_factor(ra, dec, sigma, icrs_data.ra, icrs_data.dec, db_sigma)  # type: ignore
                    P_H_D = posterior_probability_from_bayes_factor(B, prior_probability)

                    bayes_factors.append(B)
                    candidate_info.append(
                        {
                            "pgc": candidate.pgc,
                            "distance_arcsec": psi * 3600.0,
                            "bayes_factor": B,
                            "posterior_prob": P_H_D,
                            "db_error_arcsec": db_error,
                        }
                    )

                # Sort by Bayes factor
                candidate_info.sort(key=lambda x: x["bayes_factor"], reverse=True)

                for i, info in enumerate(candidate_info):
                    status = (
                        "HIGH"
                        if info["posterior_prob"] > upper_posterior_probability
                        else "LOW"
                        if info["posterior_prob"] < lower_posterior_probability
                        else "MED"
                    )
                    print(
                        f"  {i + 1}. PGC{info['pgc']}: {info['distance_arcsec']:.2f} arcsec, "
                        f"B={info['bayes_factor']:.2e}, P(H|D)={info['posterior_prob']:.6f} [{status}]"
                    )

                # Show classification logic
                high_prob = [
                    i for i, info in enumerate(candidate_info) if info["posterior_prob"] > upper_posterior_probability
                ]
                low_prob = [
                    i for i, info in enumerate(candidate_info) if info["posterior_prob"] < lower_posterior_probability
                ]

                print("  Classification logic:")
                print(f"    High probability matches: {len(high_prob)}")
                print(f"    Low probability matches: {len(low_prob)}")
                print(f"    Expected: {category}")
                print(f"    Actual: {results[obj_id].status}")


if __name__ == "__main__":
    test_bayesian_algorithm()
    test_simulated_cross_identification()
