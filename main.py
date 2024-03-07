import click
import app.commands.runserver as runserver_cmd

@click.group()
def cli():
    pass

@cli.command(short_help="Start API server")
def runserver():
    runserver_cmd.start()

if __name__ == "__main__":
    cli()
