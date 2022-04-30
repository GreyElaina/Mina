import sys

import tomli
from pdm.project.core import Project
from pdm.cli.commands.base import BaseCommand
from argparse import Namespace

class MinaPackagesListCommand(BaseCommand):
    def handle(self, project: Project, options: Namespace):
        if not (project.root / "pyproject.toml").exists():
            project.core.ui.echo(
                "No pyproject.toml found.", err=True
            )
            sys.exit(1)
        pyproj = tomli.loads((project.root / "pyproject.toml").read_text())
        mina_packages = pyproj.get("tool", {}).get("mina", {}).get("packages", [])
        if not mina_packages:
            project.core.ui.echo(
                "No mina packages found, you could add some in pyproject.toml."
            )
            sys.exit(0)
        project.core.ui.echo(
            "\n".join([
                "Found mina packages:",
                *[f" - {package}" for package in mina_packages],
            ])
        )
