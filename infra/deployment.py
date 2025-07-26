import io
import os
import pathlib
from dataclasses import dataclass, field
from typing import IO

import structlog
from fabric import Connection


@dataclass
class RemoteFile:
    local_path: pathlib.Path | str
    remote_path: pathlib.Path | str

    def __str__(self) -> str:
        return f"{self.local_path} --> {self.remote_path}"


@dataclass
class RemoteContent:
    content: str
    remote_path: pathlib.Path | str

    def __str__(self) -> str:
        return f'"{self.content}" --> {self.remote_path}'


@dataclass
class RemoteDirectory:
    local_path: pathlib.Path | str
    remote_path: pathlib.Path | str

    def _get_filenames(self) -> list[str]:
        filenames: list[str] = []

        for _, _, fnames in os.walk(self.local_path):
            filenames.extend(fnames)

        filenames.sort()

        return filenames

    def __str__(self) -> str:
        filenames = self._get_filenames()
        if len(filenames) == 0:
            return ""

        lines = []
        lines.append(f"{self.local_path} --> {self.remote_path}")

        for filename in filenames:
            lines.append(f"\t/{filename}")

        return "\n".join(lines)

    def to_files(self) -> list[RemoteFile]:
        files: list[RemoteFile] = []

        local_base = pathlib.Path(self.local_path)
        remote_base = pathlib.Path(self.remote_path)
        filenames = self._get_filenames()

        for filename in filenames:
            local_file = local_base / filename
            remote_file = remote_base / filename
            files.append(RemoteFile(local_file, remote_file))

        return files


RemoteData = RemoteFile | RemoteContent | RemoteDirectory


@dataclass
class ConnectionContext:
    host: str
    user: str
    private_key_filename: str


def _run_command(
    logger: structlog.stdlib.BoundLogger,
    connection: Connection,
    cmd: str,
):
    logger.debug("Running command", cmd=cmd)

    connection.run(cmd)


def _apply_item(
    logger: structlog.stdlib.BoundLogger,
    connection: Connection,
    path_on_remote: str | pathlib.Path,
    file_like: IO | str,
):
    remote_path = pathlib.Path(path_on_remote)

    if isinstance(file_like, str):
        logger.debug("Copying file", src=str(file_like), dst=str(remote_path))
    else:
        logger.debug("Writing file", dst=str(remote_path))

    connection.put(file_like, str(remote_path))


@dataclass
class RemoteSpec:
    data: list[RemoteData]
    root_dir: pathlib.Path
    env_vars: dict[str, str] = field(default_factory=dict)

    def add(self, data: RemoteData | list[RemoteData]):
        if isinstance(data, list):
            self.data.extend(data)
            return

        self.data.append(data)

    def __str__(self) -> str:
        lines = [
            "------- Params -------",
            f"Root directory: {self.root_dir}",
            "",
            "------- Environment variables -------",
        ]

        lines.extend(self.env_vars.keys())

        lines.extend(
            [
                "",
                "------- Directory structure -------",
            ]
        )

        for entry in self.data:
            lines.append(str(entry))

        return "\n".join(lines)

    def apply(self, ctx: ConnectionContext, logger: structlog.stdlib.BoundLogger):
        self.connection = Connection(
            host=ctx.host,
            user=ctx.user,
            connect_kwargs={"key_filename": ctx.private_key_filename},
        )
        self.logger = logger

        for item in self.data:
            if isinstance(item, RemoteFile):
                path = self.root_dir / item.remote_path
                _run_command(self.logger, self.connection, f"mkdir -p {str(path.parent)}")

                _apply_item(self.logger, self.connection, path, str(item.local_path))
            elif isinstance(item, RemoteContent):
                path = self.root_dir / item.remote_path
                _run_command(self.logger, self.connection, f"mkdir -p {str(path.parent)}")

                _apply_item(self.logger, self.connection, path, io.StringIO(item.content))
            elif isinstance(item, RemoteDirectory):
                _run_command(self.logger, self.connection, f"mkdir -p {str(self.root_dir / item.remote_path)}")
                files = item.to_files()

                for file in files:
                    _apply_item(self.logger, self.connection, self.root_dir / file.remote_path, str(file.local_path))

        _run_command(self.logger, self.connection, f"cd {self.root_dir} && docker compose pull")

    def reload(self):
        env_strings = []

        for key, value in self.env_vars.items():
            env_strings.append(f"{key}={value}")

        env_string = " ".join(env_strings)

        _run_command(self.logger, self.connection, f"cd {self.root_dir} && {env_string} docker compose up -d")
