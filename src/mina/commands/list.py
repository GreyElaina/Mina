import sys
from argparse import Namespace

from pdm.cli.commands.base import BaseCommand
from pdm.project.core import Project


class MinaPackagesListCommand(BaseCommand):
    """List all sub packages in the project."""

    def handle(self, project: Project, options: Namespace):
        mina_packages = (
            project.pyproject._data.get("tool", {}).get("mina", {}).get("packages", [])
        )
        for i in project.root.glob(".mina/*.toml"):
            name = i.name[:-5]
            if name not in mina_packages:
                mina_packages.append(name)

        if not mina_packages:
            project.core.ui.echo(
                "No mina packages found, you could add some in pyproject.toml.",
                err=True,
                style="error",
            )
            sys.exit(0)
        project.core.ui.echo(
            "\n".join(
                [
                    "Found mina packages:",
                    *[f" - {package}" for package in mina_packages],
                ]
            )
        )
