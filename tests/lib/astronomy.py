import random
import uuid


def get_ngc_name() -> str:
    return f"NGC {random.randint(1, 10000)}"


def get_eso_name() -> str:
    return f"ESO {random.randint(1, 1000)}-{random.randint(1, 100)}"


def get_2masx_name() -> str:
    ra_part = (
        f"{random.randint(0, 23):02d}{random.randint(0, 59):02d}"
        f"{random.randint(0, 59):02d}.{random.randint(0, 9)}{random.randint(0, 9)}"
    )
    dec_part = (
        f"{random.choice(['+', '-'])}{random.randint(0, 89):02d}"
        f"{random.randint(0, 59):02d}{random.randint(0, 59):02d}.{random.randint(0, 9)}"
    )
    return f"2MASX J{ra_part}{dec_part}"


def get_synthetic_data(
    n: int,
    ra_center: float,
    dec_center: float,
    ra_range: float,
    dec_range: float,
) -> list[dict]:
    data = []

    for _ in range(n):
        object_types = ["NGC", "ESO", "2MASX"]
        object_type = random.choice(object_types)

        if object_type == "NGC":
            name = get_ngc_name()
        elif object_type == "ESO":
            name = get_eso_name()
        elif object_type == "2MASX":
            name = get_2masx_name()

        ra_deg = random.uniform(ra_center - ra_range / 2, ra_center + ra_range / 2)
        dec_deg = random.uniform(dec_center - dec_range / 2, dec_center + dec_range / 2)

        ra_hours = ra_deg / 15.0

        base_error = random.uniform(0.01, 1.0)
        e_ra = base_error * random.uniform(0.8, 1.2)
        e_dec = base_error * random.uniform(0.8, 1.2)

        data.append(
            {
                "name": name,
                "ra": ra_hours,
                "dec": dec_deg,
                "e_ra": e_ra,
                "e_dec": e_dec,
                "fuzz": str(uuid.uuid4()),
            }
        )

    return data
