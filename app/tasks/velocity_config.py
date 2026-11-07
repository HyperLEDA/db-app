import pydantic

from app.lib import config


class ValueWithUncertainty(config.BaseConfigSettings):
    value: float
    error: float


class ApexConfig(config.BaseConfigSettings):
    lon: ValueWithUncertainty
    lat: ValueWithUncertainty
    vel: ValueWithUncertainty


def _default_apexes() -> dict[str, ApexConfig]:
    return {
        "heliocentric": ApexConfig(
            lon=ValueWithUncertainty(value=0.0, error=0.0),
            lat=ValueWithUncertainty(value=0.0, error=0.0),
            vel=ValueWithUncertainty(value=0.0, error=0.0),
        ),
        # https://ui.adsabs.harvard.edu/abs/2025A%26A...698A.178M/abstract
        "local_group": ApexConfig(
            lon=ValueWithUncertainty(value=94.0, error=0.7),
            lat=ValueWithUncertainty(value=-2.7, error=0.3),
            vel=ValueWithUncertainty(value=301.0, error=3.0),
        ),
        # https://ui.adsabs.harvard.edu/abs/2016A%26A...594A...8P/abstract
        "cmb": ApexConfig(
            lon=ValueWithUncertainty(value=263.99, error=0.14),
            lat=ValueWithUncertainty(value=48.26, error=0.03),
            vel=ValueWithUncertainty(value=370.06, error=0.09),
        ),
    }


class VelocityCatalogConfig(config.BaseConfigSettings):
    apexes: dict[str, ApexConfig] = pydantic.Field(default_factory=_default_apexes)


class CatalogConfig(config.BaseConfigSettings):
    velocity: VelocityCatalogConfig = pydantic.Field(default_factory=VelocityCatalogConfig)
