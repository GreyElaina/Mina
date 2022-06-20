from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from pdm.pep517._vendor import tomli
from pdm.pep517._vendor.packaging.requirements import Requirement
from pdm.pep517.api import _prepare_metadata
from pdm.pep517.api import get_requires_for_build_sdist as get_requires_for_build_sdist
from pdm.pep517.api import get_requires_for_build_wheel as get_requires_for_build_wheel
from pdm.pep517.api import (
    prepare_metadata_for_build_wheel as prepare_metadata_for_build_wheel,
)
from pdm.pep517.base import Builder
from pdm.pep517.editable import EditableBuilder
from pdm.pep517.metadata import Metadata
from pdm.pep517.sdist import SdistBuilder
from pdm.pep517.wheel import WheelBuilder


@functools.lru_cache(None)
def _get_config_root():
    cwd = Path.cwd()
    return tomli.loads((cwd / "pyproject.toml").read_text())


@functools.lru_cache(None)
def _get_root_project():
    return _get_config_root().get("project", {})


@functools.lru_cache(None)
def _get_tool_mina() -> dict[str, Any]:
    return _get_config_root().get("tool", {}).get("mina", {})


@functools.lru_cache(None)
def _get_package(package: str) -> Dict[str, Any]:
    return _get_tool_mina().get("packages", {}).get(package, {})


def _has_package(package: str) -> bool:
    return _get_package(package) is not None


def _get_build_target(
    config_settings: Optional[Mapping[str, Any]] = None
) -> str | None:
    return (
        (config_settings or {}).get("--mina-target")
        or os.environ.get("MINA_BUILD_TARGET")
        or _get_tool_mina().get("mina-build-target")
    )


def _using_override_global() -> bool:
    return _get_tool_mina().get("override-global", False)


def _using_override(package: str | None) -> bool:
    if package and _has_package(package):
        pkg = _get_package(package)
        if "override" in pkg:
            return pkg["override"]
    return _using_override_global()


def _patch_dep(_meta: Metadata, pkg_project: dict[str, Any]):
    if "dependencies" in pkg_project:
        optional_dependencies = []

        optional_deps = pkg_project["dependencies"]
        workspace_deps = _get_root_project().get("dependencies", [])
        workspace_deps = [Requirement(i) for i in workspace_deps]
        workspace_deps = {i.name: i for i in workspace_deps if i.name is not None}

        for dep in optional_deps:
            req = Requirement(dep)
            if req.name is None:
                raise ValueError(f"'{dep}' is not a valid requirement")
            if req.name not in workspace_deps:
                raise ValueError(f"{req.name} is not defined in project requirements")
            optional_dependencies.append(str(workspace_deps[req.name]))

        pkg_project["dependencies"] = _meta._convert_dependencies(optional_dependencies)

    if "optional-dependencies" in pkg_project:
        optional_dependencies = {}

        deps = pkg_project["optional-dependencies"]

        # workspace don't use optional dep: it must contains ALL deps mina required.
        workspace_deps = _get_root_project().get("dependencies", [])
        workspace_deps = [Requirement(i) for i in workspace_deps]
        workspace_deps = {i.name: i for i in workspace_deps if i.name is not None}

        for group, optional_deps in deps.items():
            group_deps = []
            for dep in optional_deps:
                req = Requirement(dep)
                if req.name is None:
                    raise ValueError(f"'{dep}' is not a valid requirement")
                if req.name not in workspace_deps:
                    raise ValueError(f"{req.name} is not defined in project requirements")
                group_deps.append(str(workspace_deps[req.name]))
            optional_dependencies[group] = group_deps

        pkg_project["optional-dependencies"] = _meta._convert_optional_dependencies(
            optional_dependencies
        )


def _patch_pdm_metadata(package: str):
    cwd = Path.cwd()
    _meta = Builder(cwd).meta

    config = tomli.loads((cwd / "pyproject.toml").read_text())

    package_conf = (
        config.get("tool", {}).get("mina", {}).get("packages", {}).get(package, None)
    )
    if package_conf is None:
        raise ValueError(f"No package named '{package}'")
    package_project = package_conf.get("project", {})

    _patch_dep(_meta, package_project)

    pdm_settings = config.get("tool", {}).get("pdm", {})

    # dev-dependencies is unnecessary for a pkg(for workspace), so it will be ignored by mina.

    if "includes" in package_conf:
        pdm_settings["includes"] = package_conf["includes"]

    if "excludes" in package_conf:
        pdm_settings["excludes"] = package_conf["excludes"]

    if "source-includes" in package_conf:
        pdm_settings["source-includes"] = package_conf["source-includes"]

    if "is-purelib" in package_conf:
        pdm_settings["is-purelib"] = package_conf["is-purelib"]

    if "entry-points" in package_conf:
        pdm_settings["entry-points"] = package_conf["entry-points"]

    if "build" in package_conf:
        pdm_settings["build"] = package_conf["build"]

    if "raw-dependencies" in package_conf and _meta.dependencies is not None:
        _meta.dependencies.extend(package_conf["raw-dependencies"])

    if _using_override(package):
        project_conf = config.get("project", {})
        _meta._metadata = dict(project_conf, **package_project)
    else:
        _meta._metadata = package_project

    _meta._tool_settings = pdm_settings
    _meta.validate(True)

    return _meta


def prepare_metadata_for_build_wheel(
    metadata_directory: str, config_settings: Optional[Mapping[str, Any]] = None
) -> str:
    """Prepare the metadata, places it in metadata_directory"""
    _patched_meta = None
    mina_target = _get_build_target(config_settings)
    if mina_target is not None:
        if not _has_package(mina_target):
            raise ValueError(f"{mina_target} is not defined as a mina package")
        _patched_meta = _patch_pdm_metadata(mina_target)  # os.chdir may break behavior
    with WheelBuilder(Path.cwd(), config_settings) as builder:
        if _patched_meta is not None:
            builder._meta = _patched_meta
        return _prepare_metadata(builder, metadata_directory)


def build_wheel(
    wheel_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
    metadata_directory: Optional[str] = None,
) -> str:
    """Builds a wheel, places it in wheel_directory"""
    _patched_meta = None
    mina_target = _get_build_target(config_settings)
    if mina_target is not None:
        if not _has_package(mina_target):
            raise ValueError(f"{mina_target} is not defined as a mina package")
        _patched_meta = _patch_pdm_metadata(mina_target)  # os.chdir may break behavior
    with WheelBuilder(Path.cwd(), config_settings) as builder:
        if _patched_meta is not None:
            builder._meta = _patched_meta
        return Path(builder.build(wheel_directory)).name


def build_sdist(
    sdist_directory: str, config_settings: Optional[Mapping[str, Any]] = None
) -> str:
    """Builds an sdist, places it in sdist_directory"""
    _patched_meta = None
    mina_target = _get_build_target(config_settings)
    if mina_target is not None:
        if not _has_package(mina_target):
            raise ValueError(f"{mina_target} is not defined as a mina package")
        _patched_meta = _patch_pdm_metadata(mina_target)  # os.chdir may break behavior
    with SdistBuilder(Path.cwd(), config_settings) as builder:
        if _patched_meta is not None:
            builder._meta = _patched_meta
        return Path(builder.build(sdist_directory)).name


get_requires_for_build_editable = get_requires_for_build_wheel


def prepare_metadata_for_build_editable(
    metadata_directory: str, config_settings: Optional[Mapping[str, Any]] = None
) -> str:
    """Prepare the metadata, places it in metadata_directory"""
    _patched_meta = None
    mina_target = _get_build_target(config_settings)
    if mina_target is not None:
        if not _has_package(mina_target):
            raise ValueError(f"{mina_target} is not defined as a mina package")
        _patched_meta = _patch_pdm_metadata(mina_target)  # os.chdir may break behavior
    with EditableBuilder(Path.cwd(), config_settings) as builder:
        if _patched_meta is not None:
            builder._meta = _patched_meta
        builder._prepare_editable()
        return _prepare_metadata(builder, metadata_directory)


def build_editable(
    wheel_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
    metadata_directory: Optional[str] = None,
) -> str:
    _patched_meta = None
    mina_target = _get_build_target(config_settings)
    if mina_target is not None:
        if not _has_package(mina_target):
            raise ValueError(f"{mina_target} is not defined as a mina package")
        _patched_meta = _patch_pdm_metadata(mina_target)  # os.chdir may break behavior
    with EditableBuilder(Path.cwd(), config_settings) as builder:
        if _patched_meta is not None:
            builder._meta = _patched_meta
        return Path(builder.build(wheel_directory)).name
