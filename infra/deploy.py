import os
import pathlib
import subprocess
from dataclasses import dataclass

import deployment
import structlog


def get_git_version() -> str:
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
    return result.stdout.strip()


@dataclass
class EnvParams:
    connection: deployment.ConnectionContext
    remote_base_path: str
    configs_env: str
    ads_token: str = ""
    postgres_password: str = ""

    _ads_token_env = "ADS_TOKEN"
    _postgres_password_env = "POSTGRES_PASSWORD"

    @classmethod
    def from_yaml(cls, path: str) -> "EnvParams":
        import yaml

        with pathlib.Path(path).open("r") as f:
            data = yaml.safe_load(f)

        data["connection"] = deployment.ConnectionContext(**data["connection"])

        params = cls(**data)
        params.ads_token = params.ads_token or os.getenv(params._ads_token_env) or ""
        params.postgres_password = params.postgres_password or os.getenv(params._postgres_password_env) or ""

        return params


def get_spec(params: EnvParams) -> deployment.RemoteSpec:
    return deployment.RemoteSpec(
        [
            deployment.RemoteFile(
                "infra/docker-compose.yaml",
                "docker-compose.yaml",
            ),
            deployment.RemoteContent(
                get_git_version(),
                "version.txt",
            ),
            deployment.RemoteDirectory(
                "postgres/migrations",
                "postgres/migrations",
            ),
            deployment.RemoteDirectory(
                "infra/configs/nginx",
                "configs",
            ),
            deployment.RemoteDirectory(
                pathlib.Path("configs") / params.configs_env,
                "configs",
            ),
        ],
        root_dir=pathlib.Path(params.remote_base_path),
        env_vars={
            "ADS_TOKEN": params.ads_token,
            "POSTGRES_PASSWORD": params.postgres_password,
        },
    )


if __name__ == "__main__":
    logger = structlog.get_logger()

    params = EnvParams.from_yaml("infra/settings/test.yaml")

    spec = get_spec(params)
    print(spec)

    answer = input("Apply spec? [y/n] ")
    if answer == "y":
        spec.apply(params.connection, logger)
        spec.reload()
    else:
        print("Deploy cancelled")
