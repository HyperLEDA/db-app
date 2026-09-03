from typing import final

import pytest

from app.lib import commands
from app.lib.commands import interface


def test_successful_execution() -> None:
    prepared = False
    executed = False
    cleaned = False

    @final
    class TestCommand(interface.Command):
        def prepare(self):
            nonlocal prepared
            prepared = True

        def run(self):
            nonlocal executed
            executed = True

        def cleanup(self):
            nonlocal cleaned
            cleaned = True

    commands.run(TestCommand())
    assert prepared is True
    assert executed is True
    assert cleaned is True


def test_failed_during_prepare() -> None:
    prepared = False
    executed = False
    cleaned = False

    @final
    class TestCommand(interface.Command):
        def prepare(self):
            nonlocal prepared
            raise Exception("Fail")

        def run(self):
            nonlocal executed
            executed = True

        def cleanup(self):
            nonlocal cleaned
            cleaned = True

    with pytest.raises(Exception):
        commands.run(TestCommand())

    assert prepared is False
    assert executed is False
    assert cleaned is True


def test_failed_during_run() -> None:
    prepared = False
    executed = False
    cleaned = False

    @final
    class TestCommand(interface.Command):
        def prepare(self):
            nonlocal prepared
            prepared = True

        def run(self):
            nonlocal executed
            raise Exception("Fail")

        def cleanup(self):
            nonlocal cleaned
            cleaned = True

    with pytest.raises(Exception):
        commands.run(TestCommand())

    assert prepared is True
    assert executed is False
    assert cleaned is True


def test_failed_during_cleanup() -> None:
    prepared = False
    executed = False
    cleaned = False

    @final
    class TestCommand(interface.Command):
        def prepare(self):
            nonlocal prepared
            prepared = True

        def run(self):
            nonlocal executed
            executed = True

        def cleanup(self):
            nonlocal cleaned
            raise Exception("Fail")

    commands.run(TestCommand())

    assert prepared is True
    assert executed is True
    assert cleaned is False
