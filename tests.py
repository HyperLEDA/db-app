import click

from tests.regression import upload_simple_table, upload_vizier_table


@click.group()
def cli():
    pass


@cli.command()
def regression_tests():
    upload_simple_table.run()
    upload_vizier_table.run()


if __name__ == "__main__":
    cli()
