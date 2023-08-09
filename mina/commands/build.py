from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    import tomllib as tomli  # type: ignore
except ImportError:
    try:
        from pdm.backend._vendor import tomli
    except ImportError:
        import tomli
from pdm.builders.sdist import SdistBuilder
from pdm.builders.wheel import WheelBuilder
from pdm.cli.commands.base import BaseCommand
from pdm.exceptions import ProjectError
from pdm.project.core import Project


def do_build_mina(
    project: Project,
    packages: list[str],
    option_sdist: bool = True,
    option_wheel: bool = True,
    option_dest: str = "dist",
    option_clean: bool = True,
    config_settings: dict[str, str] | None = None,
):
    if project.is_global:
        project.core.ui.echo("You can't build packages in global project.", err=True)
        raise ProjectError("Global project not supported")
    if not option_wheel and not option_sdist:
        project.core.ui.echo("You must build at least one of sdist or wheel.", err=True)
        raise ProjectError("No build type specified")
    dest = Path(option_dest).absolute()
    if option_clean:
        shutil.rmtree(dest, ignore_errors=True)
    artifacts: list[str] = []
    for package in packages:
        settings = (config_settings or {}).copy()
        settings.setdefault("--mina-target", package)
        project.core.ui.echo(f"Building package {package}...")
        with project.core.ui.logging("Building packages"):
            if option_sdist:
                project.core.ui.echo("  - Building sdist")
                loc = SdistBuilder(project.root, project.environment).build(
                    option_dest, settings
                )
                project.core.ui.echo(f"    - completed: {loc}")
                artifacts.append(loc)
            if option_wheel:
                project.core.ui.echo("  - Building wheel")
                loc = WheelBuilder(project.root, project.environment).build(
                    option_dest, settings
                )
                project.core.ui.echo(f"    - completed: {loc}")
                artifacts.append(loc)
            project.core.ui.echo(f"{package} build completed.")
    project.core.ui.echo(
        f"Successfully built {len(packages)} packages: {len(artifacts)} artifacts"
    )
    return artifacts


class MinaCommandNamespace:
    packages: list[str]
    all: bool
    sdist: bool
    wheel: bool
    dest: str
    clean: bool
    config_setting: list[str]


class MinaBuildCommand(BaseCommand):
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "packages",
            nargs="*",
            help="Packages to build, which must be defined in pyproject.toml.",
        )
        parser.add_argument(
            "-a",
            "--all",
            default=False,
            action="store_true",
            help="Build all packages.",
        )
        parser.add_argument(
            "--no-sdist",
            dest="sdist",
            default=True,
            action="store_false",
            help="Don't build source tarballs",
        )
        parser.add_argument(
            "--no-wheel",
            dest="wheel",
            default=True,
            action="store_false",
            help="Don't build wheels",
        )
        parser.add_argument(
            "-d", "--dest", default="dist", help="Target directory to put artifacts"
        )
        parser.add_argument(
            "--no-clean",
            dest="clean",
            default=True,
            action="store_false",
            help="Do not clean the target directory",
        )
        parser.add_argument(
            "--config-setting",
            "-C",
            action="append",
            default=[],
            help="Pass options to the backend. options with a value must be "
            'specified after "=": "--config-setting=--opt(=value)" '
            'or "-C--opt(=value)"',
        )

    def handle(self, project: Project, options: MinaCommandNamespace):
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

        packages = options.packages

        if options.all:
            if packages:
                raise ProjectError("Cannot specify packages and --all")
            packages = mina_packages

        if not packages:
            raise ProjectError("No package specified")

        errors: list[str] = [
            package for package in packages if package not in mina_packages
        ]
        if errors:
            raise ProjectError(f"Package(s) not found: {', '.join(errors)}")

        config_settings = {}
        for item in options.config_setting:
            name, _, value = item.partition("=")
            if name not in config_settings:
                config_settings[name] = value
            else:
                if not isinstance(config_settings[name], list):
                    config_settings[name] = [config_settings[name]]
                config_settings[name].append(value)
        artifacts = do_build_mina(
            project,
            packages,
            options.sdist,
            options.wheel,
            options.dest,
            options.clean,
            config_settings,
        )
        # artifacts 后面还可以拿来做其他的事情, 比如 publish.
