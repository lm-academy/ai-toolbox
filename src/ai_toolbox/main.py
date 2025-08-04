import click


@click.group()
def cli():
    """Main command group for the AI toolbox."""
    pass


@click.command()
def hello():
    """Prints a greeting message."""
    click.echo("Hello from the AI toolbox!")


cli.add_command(hello)

if __name__ == "__main__":
    cli()
