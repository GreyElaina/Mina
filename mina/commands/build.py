from __future__ import annotations
import shutil
from pdm.builders.sdist import SdistBuilder
from pdm.builders.wheel import WheelBuilder
from pdm.project.core import Project
from pdm.cli.commands.base import BaseCommand
from argparse import Namespace
from pdm.cli.actions import do_build as do_build_pdm
import argparse
from pdm.exceptions import ProjectError
from pathlib import Path

def do_build_mina(
    project: Project,
    package: str,
    option_sdist: bool = True,
    option_wheel: bool = True,
    option_dest: str = "dist",
    option_clean: bool = True,
    config_settings: dict[str, str] | None = None
):
    if project.is_global:
        project.core.ui.echo(
            "You can't build packages in global project.", err=True
        )
        raise ProjectError("Global project not supported")
    if not option_wheel and not option_sdist:
        project.core.ui.echo(
            "You must build at least one of sdist or wheel.", err=True
        )
        raise ProjectError("No build type specified")
    dest = Path(option_dest).absolute()
    if option_clean:
        shutil.rmtree(dest, ignore_errors=True)
    artifacts: list[str] = []
    project.core.ui.echo(f"Building for package {package}...")
    with project.core.ui.logging("Building packages"):
        if option_sdist:
            project.core.ui.echo("  - Building sdist")
            loc = SdistBuilder(project.root, project.environment).build(
                option_dest, config_settings
            )
            project.core.ui.echo(f"    - completed: {loc}")
            artifacts.append(loc)
        if option_wheel:
            project.core.ui.echo("  - Building wheel")
            loc = WheelBuilder(project.root, project.environment).build(
                option_dest, config_settings
            )
            project.core.ui.echo(f"    - completed: {loc}")
            artifacts.append(loc)
    project.core.ui.echo(f"Build completed: {len(artifacts)} artifacts")
    return artifacts

class MinaBuildCommand(BaseCommand):
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "package",
            #nargs="?",
            help="The package to build, which must be defined in pyproject.toml.",
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
            help="Pass options to the backend. options with a value must be "
            'specified after "=": "--config-setting=--opt(=value)" '
            'or "-C--opt(=value)"',
        )

    def handle(self, project: Project, options: Namespace):
        package = options.package
        config_settings = {"--package": package}
        if options.config_setting:
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
            package,
            options.sdist,
            options.wheel,
            options.dest,
            options.clean,
            config_settings
        )
        # artifacts 后面还可以拿来做其他的事情, 比如 publish.