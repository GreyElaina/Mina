from argparse import ArgumentParser, Namespace
from typing import TYPE_CHECKING

from pdm.cli.commands.base import BaseCommand
from pdm.project.core import Project

from mina.commands.build import MinaBuildCommand
from mina.commands.list import MinaPackagesListCommand

if TYPE_CHECKING:
    from pdm.core import Core


class MinaCommand(BaseCommand):
    """Mina command."""

    def add_arguments(self, parser: ArgumentParser):
        self.parser = parser
        subparser = parser.add_subparsers()
        MinaPackagesListCommand.register_to(subparser, "list")
        MinaBuildCommand.register_to(subparser, "build")

    def handle(self, project: Project, options: Namespace) -> None:
        self.parser.print_help()


def ensure_pdm(core: "Core"):
    core.register_command(MinaCommand, "mina")
