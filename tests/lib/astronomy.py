import random
import uuid


def generate_synthetic_astronomical_data(n: int) -> list[dict]:
    data = []

    for _ in range(n):
        object_types = ["NGC", "IC", "M", "PGC", "UGC", "ESO", "2MASX", "SDSS"]
        object_type = random.choice(object_types)

        if object_type in ["NGC", "IC", "M"]:
            name = f"{object_type} {random.randint(1, 10000)}"
        elif object_type == "PGC":
            name = f"{object_type} {random.randint(1, 1000000)}"
        elif object_type == "UGC":
            name = f"{object_type} {random.randint(1, 10000)}"
        elif object_type == "ESO":
            name = f"{object_type} {random.randint(1, 1000)}-{random.randint(1, 100)}"
        elif object_type == "2MASX":
            ra_part = (
                f"{random.randint(0, 23):02d}{random.randint(0, 59):02d}"
                f"{random.randint(0, 59):02d}.{random.randint(0, 9)}{random.randint(0, 9)}"
            )
            dec_part = (
                f"{random.choice(['+', '-'])}{random.randint(0, 89):02d}"
                f"{random.randint(0, 59):02d}{random.randint(0, 59):02d}.{random.randint(0, 9)}"
            )
            name = f"{object_type} J{ra_part}{dec_part}"
        else:  # SDSS
            ra_part = (
                f"{random.randint(0, 23):02d}{random.randint(0, 59):02d}"
                f"{random.randint(0, 59):02d}.{random.randint(0, 9)}{random.randint(0, 9)}"
            )
            dec_part = (
                f"{random.choice(['+', '-'])}{random.randint(0, 89):02d}"
                f"{random.randint(0, 59):02d}{random.randint(0, 59):02d}.{random.randint(0, 9)}"
            )
            name = f"{object_type} J{ra_part}{dec_part}"

        ra_deg = random.uniform(0, 360)
        ra_hours = ra_deg / 15.0

        dec_deg = random.uniform(-90, 90)

        base_error = random.uniform(0.01, 1.0)
        e_ra = base_error * random.uniform(0.8, 1.2)
        e_dec = base_error * random.uniform(0.8, 1.2)

        # Generate unique fuzz identifier
        fuzz_id = str(uuid.uuid4())

        data.append(
            {
                "name": name,
                "ra": ra_hours,
                "dec": dec_deg,
                "e_ra": e_ra,
                "e_dec": e_dec,
                "fuzz": fuzz_id,
            }
        )

    return data
