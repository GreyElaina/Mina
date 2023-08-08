import sys
from pathlib import Path
from argparse import Namespace

try:
    import tomllib as tomli  # type: ignore
except ImportError:
    try:
        from pdm.backend._vendor import tomli
    except ImportError:
        import tomli
from pdm.cli.commands.base import BaseCommand
from pdm.project.core import Project


class MinaPackagesListCommand(BaseCommand):
    def handle(self, project: Project, options: Namespace):
        if not (project.root / "pyproject.toml").exists():
            project.core.ui.echo("No pyproject.toml found.", err=True)
            sys.exit(1)
        pyproj = tomli.loads(
            (project.root / "pyproject.toml").read_text(encoding="utf-8")
        )
        mina_packages = pyproj.get("tool", {}).get("mina", {}).get("packages", [])
        for i in project.root.glob(".mina/*.toml"):
            name = i.name[:-5]
            if name not in mina_packages:
                mina_packages.append(name)
                
        if not mina_packages:
            project.core.ui.echo(
                "No mina packages found, you could add some in pyproject.toml."
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
