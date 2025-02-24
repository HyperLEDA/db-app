import unittest
from typing import final

from app.lib import commands
from app.lib.commands import interface


class CommandsTest(unittest.TestCase):
    def test_successful_execution(self):
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
        self.assertEqual(prepared, True)
        self.assertEqual(executed, True)
        self.assertEqual(cleaned, True)

    def test_failed_during_prepare(self):
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

        with self.assertRaises(Exception):
            commands.run(TestCommand())

        self.assertEqual(prepared, False)
        self.assertEqual(executed, False)
        self.assertEqual(cleaned, True)

    def test_failed_during_run(self):
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

        with self.assertRaises(Exception):
            commands.run(TestCommand())

        self.assertEqual(prepared, True)
        self.assertEqual(executed, False)
        self.assertEqual(cleaned, True)

    def test_failed_during_cleanup(self):
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

        self.assertEqual(prepared, True)
        self.assertEqual(executed, True)
        self.assertEqual(cleaned, False)
