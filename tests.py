import pathlib

import click

from tests.lib import colors
from tests.regression import upload_simple_table


@click.group()
def cli():
    pass


tests = [upload_simple_table]


@cli.command()
def regression_tests():
    for test in tests:
        test_name = pathlib.Path(str(test.__file__)).stem.replace("_", " ")
        print(f"---- {colors.color(test_name, 'blue')} ----")
        test.run()


if __name__ == "__main__":
    cli()
