import pathlib
import subprocess
from dataclasses import dataclass

import deployment
import structlog


def get_git_version() -> str:
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def get_spec(base_path: str, configs_env: str) -> deployment.RemoteSpec:
    remote_base_path = pathlib.Path(base_path)

    return deployment.RemoteSpec(
        [
            deployment.RemoteFile(
                "infra/docker-compose.yaml",
                "docker-compose.yaml",
            ),
            deployment.RemoteFile(
                "infra/.env.remote",
                ".env.local",
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
                pathlib.Path("configs") / configs_env,
                "configs",
            ),
        ],
        root_dir=remote_base_path,
    )


@dataclass
class EnvParams:
    connection: deployment.ConnectionContext
    remote_base_path: str
    configs_env: str

    @classmethod
    def from_yaml(cls, path: str) -> "EnvParams":
        import yaml

        with pathlib.Path(path).open("r") as f:
            data = yaml.safe_load(f)

        data["connection"] = deployment.ConnectionContext(**data["connection"])

        return cls(**data)


if __name__ == "__main__":
    logger = structlog.get_logger()

    params = EnvParams.from_yaml("infra/settings/test.yaml")

    spec = get_spec(params.remote_base_path, params.configs_env)
    print(spec)

    answer = input("Apply spec? [y/n] ")
    if answer == "y":
        spec.apply(params.connection, logger)
    else:
        print("Deploy cancelled")
