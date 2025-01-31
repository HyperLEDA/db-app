from typing import final

from app.lib import commands
from tests.regression import upload_simple_table


@final
class RegressionTestsCommand(commands.Command):
    def prepare(self):
        pass

    def run(self):
        upload_simple_table.run()

    def cleanup(self):
        pass
