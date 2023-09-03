from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, cast

try:
    import tomllib as tomli  # type: ignore
except ImportError:
    try:
        from pdm.backend._vendor import tomli
    except ImportError:
        import tomli  # type: ignore

from pdm.backend._vendor.packaging.requirements import Requirement
from pdm.backend import \
    get_requires_for_build_sdist as get_requires_for_build_sdist
from pdm.backend import \
    get_requires_for_build_wheel as get_requires_for_build_wheel
from pdm.backend.base import Builder
from pdm.backend.config import Metadata, BuildConfig


@functools.lru_cache(None)
def _get_config_root():
    cwd = Path.cwd()
    return tomli.loads((cwd / "pyproject.toml").read_text(encoding="utf-8"))


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


def _patch_dep(pkg_project: dict[str, Any]):
    if "dependencies" in pkg_project:
        dependencies: list[str] = []

        deps = cast(list[str], pkg_project["dependencies"])
        workspace_deps_origin: list[str] = _get_root_project().get("dependencies", [])
        workspace_deps_convert = [Requirement(i) for i in workspace_deps_origin]
        workspace_deps_map = {
            i.name: i for i in workspace_deps_convert if i.name is not None
        }

        for dep in deps:
            req = Requirement(dep)
            if req.name is None:
                raise ValueError(f"'{dep}' is not a valid requirement")
            if req.name not in workspace_deps_map:
                raise ValueError(f"{req.name} is not defined in project requirements")
            dependencies.append(str(workspace_deps_map[req.name]))

        pkg_project["dependencies"] = dependencies

    if "optional-dependencies" in pkg_project:
        optional_dependencies: dict[str, list[str]] = {}

        optional_dep_groups: dict[str, list[str]] = pkg_project["optional-dependencies"]

        # workspace don't use optional dep: it must contains ALL deps mina required.
        workspace_deps_origin: list[str] = _get_root_project().get("dependencies", [])
        workspace_deps_convert = [Requirement(i) for i in workspace_deps_origin]
        workspace_deps_map = {
            i.name: i for i in workspace_deps_convert if i.name is not None
        }

        for group, optional_deps in optional_dep_groups.items():
            group_deps = []
            for dep in optional_deps:
                req = Requirement(dep)
                if req.name is None:
                    raise ValueError(f"'{dep}' is not a valid requirement")
                if req.name not in workspace_deps_map:
                    raise ValueError(
                        f"{req.name} is not defined in project requirements"
                    )
                group_deps.append(str(workspace_deps_map[req.name]))
            optional_dependencies[group] = group_deps

        pkg_project["optional-dependencies"] = optional_dependencies


def _get_standalone_config(pkg: str):
    config_file = Path.cwd() / ".mina" / f"{pkg}.toml"
    if not config_file.exists():
        return
    
    return tomli.loads(config_file.read_text())


def _patch_pdm_config(package: str):
    cwd = Path.cwd()
    config = Builder(cwd).config

    package_conf = _get_standalone_config(package)
    if package_conf is not None:
        package_conf.setdefault("includes", []).append(f".mina/{package}.toml")
    else:
        package_conf = (
            config.data.get("tool", {})
            .get("mina", {})
            .get("packages", {})
            .get(package, None)
        )
        if package_conf is None:
            raise ValueError(f"No package named '{package}'")

    package_project = package_conf.get("project", {})

    _patch_dep(package_project)

    pdm_settings = config.data.get("tool", {}).get("pdm", {}).get("build", {})

    # dev-dependencies is unnecessary for a pkg(for workspace), so it will be ignored by mina.

    if "custom-hook" in package_conf:
        pdm_settings["custom-hook"] = package_conf["custom-hook"]

    if "includes" in package_conf:
        pdm_settings["includes"] = package_conf["includes"]

    if "excludes" in package_conf:
        pdm_settings["excludes"] = package_conf["excludes"]

    if "source-includes" in package_conf:
        pdm_settings["source-includes"] = package_conf["source-includes"]

    if "is-purelib" in package_conf:
        pdm_settings["is-purelib"] = package_conf["is-purelib"]

    if "run-setuptools" in package_conf:
        pdm_settings["run-setuptools"] = package_conf["run-setuptools"]

    if "package-dir" in package_conf:
        pdm_settings["package-dir"] = package_conf["package-dir"]

    if "editable-backend" in package_conf:
        pdm_settings["editable-backend"] = package_conf["editable-backend"]

    if "wheel-data" in package_conf:
        pdm_settings["wheel-data"] = package_conf["wheel-data"]

    if "entry-points" in package_conf:
        if "entry-points" not in package_project:
            package_project["entry-points"] = {}
        for group, entry_points in package_conf["entry-points"].items():
            if group not in package_project["entry-points"]:
                package_project["entry-points"][group] = {}
            package_project["entry-points"][group].update(entry_points)

    if "scripts" in package_conf:
        package_project.setdefault("entry-points", {})[
            "console_scripts"
        ] = package_conf["scripts"]
    if "gui-scripts" in package_conf:
        package_project.setdefault("entry-points", {})["gui_scripts"] = package_conf[
            "gui-scripts"
        ]

    if (
        "raw-dependencies" in package_conf
        and config.metadata.get("dependencies") is not None
    ):
        package_project["dependencies"].extend(package_conf["raw-dependencies"])
    if _using_override(package):
        project_conf = config.data["project"]

        def merge(source: dict, target: dict):
            for key, value in target.items():
                if key in source and isinstance(value, list):
                        source[key].extend(value)
                elif key in source and isinstance(value, dict):
                    merge(source[key], value)
                else:
                    source[key] = value
            return source

        config.data["project"] = merge(project_conf, package_project)
    else:
        config.data["project"] = package_project

    config.data["tool"].setdefault("pdm", {})["build"] = pdm_settings
    config.validate(config.data, config.root)
    config.metadata = Metadata(config.data["project"])
    config.build_config = BuildConfig(config.root, pdm_settings)
    return config


def prepare_metadata_for_build_wheel(
    metadata_directory: str, config_settings: Optional[Mapping[str, Any]] = None
) -> str:
    """Prepare the metadata, places it in metadata_directory"""
    from pdm.backend.wheel import WheelBuilder

    _patched_config = None
    mina_target = _get_build_target(config_settings)
    if mina_target is not None:
        if not _has_package(mina_target):
            raise ValueError(f"{mina_target} is not defined as a mina package")
        _patched_config = _patch_pdm_config(mina_target)  # os.chdir may break behavior
    with WheelBuilder(Path.cwd(), config_settings) as builder:
        if _patched_config is not None:
            builder.config = _patched_config
        return builder.prepare_metadata(metadata_directory).name


def build_wheel(
    wheel_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
    metadata_directory: Optional[str] = None,
) -> str:
    """Builds a wheel, places it in wheel_directory"""
    from pdm.backend.wheel import WheelBuilder

    _patched_config = None
    mina_target = _get_build_target(config_settings)
    if mina_target is not None:
        if not _has_package(mina_target):
            raise ValueError(f"{mina_target} is not defined as a mina package")
        _patched_config = _patch_pdm_config(mina_target)  # os.chdir may break behavior

    with WheelBuilder(Path.cwd(), config_settings) as builder:
        if _patched_config is not None:
            builder.config = _patched_config
        return builder.build(
            wheel_directory, metadata_directory=metadata_directory
        ).name


def build_sdist(
    sdist_directory: str, config_settings: Optional[Mapping[str, Any]] = None
) -> str:
    """Builds an sdist, places it in sdist_directory"""
    from pdm.backend.sdist import SdistBuilder

    _patched_config = None
    mina_target = _get_build_target(config_settings)
    if mina_target is not None:
        if not _has_package(mina_target):
            raise ValueError(f"{mina_target} is not defined as a mina package")
        _patched_config = _patch_pdm_config(mina_target)  # os.chdir may break behavior
    with SdistBuilder(Path.cwd(), config_settings) as builder:
        if _patched_config is not None:
            builder.config = _patched_config
        return builder.build(sdist_directory).name


get_requires_for_build_editable = get_requires_for_build_wheel


def prepare_metadata_for_build_editable(
    metadata_directory: str, config_settings: Optional[Mapping[str, Any]] = None
) -> str:
    """Prepare the metadata, places it in metadata_directory"""
    from pdm.backend.editable import EditableBuilder

    _patched_config = None
    mina_target = _get_build_target(config_settings)
    if mina_target is not None:
        if not _has_package(mina_target):
            raise ValueError(f"{mina_target} is not defined as a mina package")
        _patched_config = _patch_pdm_config(mina_target)  # os.chdir may break behavior
    with EditableBuilder(Path.cwd(), config_settings) as builder:
        if _patched_config is not None:
            builder.config = _patched_config
        return builder.prepare_metadata(metadata_directory).name


def build_editable(
    wheel_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
    metadata_directory: Optional[str] = None,
) -> str:
    from pdm.backend.editable import EditableBuilder

    _patched_config = None
    mina_target = _get_build_target(config_settings)
    if mina_target is not None:
        if not _has_package(mina_target):
            raise ValueError(f"{mina_target} is not defined as a mina package")
        _patched_config = _patch_pdm_config(mina_target)  # os.chdir may break behavior
    with EditableBuilder(Path.cwd(), config_settings) as builder:
        if _patched_config is not None:
            builder.config = _patched_config
        return builder.build(
            wheel_directory, metadata_directory=metadata_directory
        ).name
