import pathlib
import subprocess

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


test_ctx = deployment.ConnectionContext(
    "89.169.133.242",
    "kraysent",
    "/Users/kraysent/.ssh/hyperleda_rsa",
)

if __name__ == "__main__":
    logger = structlog.get_logger()

    spec = get_spec("/home/kraysent/hyperleda", "test")
    print(spec)

    answer = input("Apply spec? [y/n] ")
    if answer == "y":
        deployment.apply(test_ctx, spec, logger)
    else:
        print("Deploy cancelled")
