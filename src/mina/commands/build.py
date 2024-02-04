from __future__ import annotations

import argparse
import os
import shutil
from typing import TYPE_CHECKING

from pdm.cli.commands.build import Command as BuildCommand
from pdm.cli.hooks import HookManager
from pdm.exceptions import PdmUsageError
from pdm.project import Project


class MinaCommandNamespace:
    packages: list[str]
    all: bool
    sdist: bool
    wheel: bool
    dest: str
    clean: bool
    config_setting: list[str]
    skip: list[str] | None


class MinaBuildCommand(BuildCommand):
    """Build specific sub package or all packages."""

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
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

    def handle(self, project: Project, options: argparse.Namespace):
        if TYPE_CHECKING:
            assert isinstance(options, MinaCommandNamespace)

        config_settings = {}
        if options.config_setting:
            for item in options.config_setting:
                name, _, value = item.partition("=")
                if name not in config_settings:
                    config_settings[name] = value
                else:
                    if not isinstance(config_settings[name], list):
                        config_settings[name] = [config_settings[name]]
                    config_settings[name].append(value)

        mina_packages = (
            project.pyproject._data.get("tool", {}).get("mina", {}).get("packages", [])
        )
        for i in project.root.glob(".mina/*.toml"):
            name = i.stem
            if name not in mina_packages:
                mina_packages.append(name)

        packages = options.packages

        if options.all:
            if packages:
                raise PdmUsageError("Cannot specify packages and --all at the same time")
            packages = mina_packages

        if not packages:
            raise PdmUsageError("No package specified")

        errors: list[str] = [
            package for package in packages if package not in mina_packages
        ]
        if errors:
            raise PdmUsageError(f"Package(s) not found: {', '.join(errors)}")

        hooks = HookManager(project, options.skip)
        if options.clean:
            dest = options.dest
            if not os.path.isabs(dest):
                dest = project.root.joinpath(dest).as_posix()
            shutil.rmtree(dest, ignore_errors=True)
        for package in packages:
            settings = {**config_settings, "mina-target": package}
            self.do_build(
                project,
                sdist=options.sdist,
                wheel=options.wheel,
                dest=options.dest,
                clean=False,
                config_settings=settings,
                hooks=hooks,
            )
