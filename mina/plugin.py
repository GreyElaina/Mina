from argparse import ArgumentParser, Namespace
from typing import TYPE_CHECKING
from mina.commands.build import MinaBuildCommand
from mina.commands.list import MinaPackagesListCommand
from pdm.project.core import Project
from pdm.cli.commands.base import BaseCommand

if TYPE_CHECKING:
    from pdm.core import Core


class HelloCommand(BaseCommand):
    """Say hello to the specified person.
    If none is given, will read from "hello.name" config.
    """

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("-n", "--name", help="the person's name to whom you greet")

    def handle(self, project: Project, options: Namespace):
        print(project, options.name)
        # name = options.name or project.config["hello.name"]
        # print(f"Hello, {name}")

class MinaCommand(BaseCommand):
    """Mina command.
    """

    def add_arguments(self, parser: ArgumentParser):
        self.parser = parser
        subparser = parser.add_subparsers()
        MinaPackagesListCommand.register_to(subparser, "list")
        MinaBuildCommand.register_to(subparser, "build")

    def handle(self, project: Project, options: Namespace) -> None:
        self.parser.print_help()


def ensure_pdm(core: "Core"):
    core.register_command(HelloCommand, "hello")
    core.register_command(MinaCommand, "mina")
