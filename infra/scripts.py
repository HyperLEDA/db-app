import os
from pathlib import Path

import click

REMOTE_BASE_PATH = "~/hyperleda/"


@click.group()
def cli():
    pass


def run_cmd(cmd: str):
    print(f"Running: \033[33m{cmd}\033[0m")
    os.system(cmd)


@cli.command()
@click.option(
    "--host",
    "-h",
    help="Host to deploy to",
    default=lambda: os.environ.get("BACKEND_HOST", ""),
)
@click.option(
    "--user",
    "-u",
    help="User to deploy as",
    default=lambda: os.environ.get("BACKEND_USER", ""),
)
def copy_files(host: str, user: str):
    if host == "" or user == "":
        print("Please provide host and user")
        return

    paths_to_copy = {
        "infra/docker-compose.yaml": "docker-compose.yaml",
        "postgres/": "",
        "infra/configs/": "",
        "configs/": "",
        "infra/.env.remote": ".env.local",
    }

    os.chdir(Path(__file__).parent.parent)

    run_cmd(f"ssh {user}@{host} -T 'mkdir -p {REMOTE_BASE_PATH}'")

    for src, dst in paths_to_copy.items():
        if Path(src).is_dir():
            cmd = f"scp -r {src} {user}@{host}:{REMOTE_BASE_PATH}{dst}"
        else:
            cmd = f"scp {src} {user}@{host}:{REMOTE_BASE_PATH}{dst}"

        run_cmd(cmd)

    run_cmd(f'echo `git rev-parse --short HEAD` | ssh {user}@{host} -T "cat > ~/hyperleda/version.txt"')
    run_cmd(
        f"ssh {user}@{host} -T 'cd {REMOTE_BASE_PATH} && set -a && . .env.local && set +a  && docker compose up -d'"
    )


@cli.command()
@click.option(
    "--host",
    "-h",
    help="Host to deploy to",
    default=lambda: os.environ.get("BACKEND_HOST", ""),
)
@click.option(
    "--user",
    "-u",
    help="User to deploy as",
    default=lambda: os.environ.get("BACKEND_USER", ""),
)
def deploy(host: str, user: str):
    if host == "" or user == "":
        print("Please provide host and user")
        return

    run_cmd(
        f"ssh {user}@{host} -T 'cd {REMOTE_BASE_PATH} && set -a && . .env.local && set +a  && docker compose up -d'"
    )


if __name__ == "__main__":
    cli()
