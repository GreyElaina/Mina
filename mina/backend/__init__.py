from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from pdm.pep517._vendor import tomli
from pdm.pep517._vendor.packaging.requirements import Requirement
from pdm.pep517.api import _prepare_metadata
from pdm.pep517.api import get_requires_for_build_sdist as get_requires_for_build_sdist
from pdm.pep517.api import get_requires_for_build_wheel as get_requires_for_build_wheel
from pdm.pep517.api import (
    prepare_metadata_for_build_wheel as prepare_metadata_for_build_wheel,
)
from pdm.pep517.editable import EditableBuilder
from pdm.pep517.metadata import Metadata
from pdm.pep517.sdist import SdistBuilder
from pdm.pep517.wheel import WheelBuilder


def _get_tool_mina() -> dict[str, Any]:
    cwd = Path.cwd()
    config = tomli.loads((cwd / "pyproject.toml").read_text())

    return config.get("tool", {}).get("mina", {})


def _has_package(package: str) -> bool:
    package_conf = _get_tool_mina().get("packages", {}).get(package, None)
    return package_conf is not None


def _using_mina_package_structure() -> bool:
    return _get_tool_mina().get("enabled", False)


def _get_build_target(
    config_settings: Optional[Mapping[str, Any]] = None
) -> str | None:
    return (
        (config_settings or {}).get("--package")
        or os.environ.get("MINA_BUILD_TARGET")
        or _get_tool_mina().get("mina-build-target")
    )


def _patch_pdm_metadata(package: str):
    cwd = Path.cwd()
    _meta = Metadata(cwd / "pyproject.toml")

    config = tomli.loads((cwd / "pyproject.toml").read_text())

    package_conf = (
        config.get("tool", {}).get("mina", {}).get("packages", {}).get(package, None)
    )

    project_conf = config.get("project", {})

    project_deps = project_conf.get("dependencies", [])
    project_deps = [Requirement(i) for i in project_deps]
    project_deps = {i.name: i for i in project_deps if i.name is not None}

    optional_deps = project_conf.get("optional-dependencies", {})
    optional_deps = [Requirement(i) for i in optional_deps]
    optional_deps = {i.name: i for i in optional_deps if i.name is not None}

    if package_conf is None:
        raise ValueError(f"No package named '{package}'")

    project_conf["mina-package"] = package

    if "dependencies" in package_conf:
        package_dependencies = []
        # 处理 requirement, 将其 patch 到 global requirements
        for pkgreq in package_conf["dependencies"]:
            req = Requirement(pkgreq)
            if req.name is None:
                raise ValueError(f"'{pkgreq}' is not a valid requirement")
            if req.name not in project_deps:
                raise ValueError(f"{req.name} is not defined in project requirements")
            package_dependencies.append(str(project_deps[req.name]))

        package_dependencies = _meta._convert_dependencies(package_dependencies)
        package_conf["dependencies"] = package_dependencies

    if "optional-dependencies" in package_conf:
        package_optional_dependencies: Dict[str, List[str]] = {}
        # 处理 requirement, 将其 patch 到 global requirements
        for setname, pkgreq in package_conf["optional-dependencies"].items():
            req = Requirement(pkgreq)
            if req.name is None:
                raise ValueError(f"'{pkgreq}' is not a valid requirement")
            package_optional_dependencies.setdefault(setname, [])
            if req.name in project_deps:
                package_optional_dependencies[setname].append(
                    str(project_deps[req.name])
                )
            elif req.name in optional_deps:
                package_optional_dependencies[setname].append(
                    str(optional_deps[req.name])
                )
            else:
                raise ValueError(
                    f"{req.name} is not defined in project requirements or optional-dependencies"
                )

        package_optional_dependencies = _meta._convert_optional_dependencies(
            package_optional_dependencies
        )
        package_conf["optional-dependencies"] = package_optional_dependencies

    pdm_settings = config.get("tool", {}).get("pdm", {})

    # dev-dependencies is unnecessary for a pkg, it will be ignored by mina.
    if "includes" in package_conf:
        pdm_settings["includes"] = package_conf["includes"]

    if "excludes" in package_conf:
        pdm_settings["excludes"] = package_conf["excludes"]

    if "source-includes" in package_conf:
        pdm_settings["source-includes"] = package_conf["source-includes"]

    if "is-purelib" in package_conf:
        pdm_settings["is-purelib"] = package_conf["is-purelib"]

    _meta._metadata = dict(project_conf, **package_conf)
    _meta._tool_settings = pdm_settings
    # print(_meta.validate(False))

    return _meta


def prepare_metadata_for_build_wheel(
    metadata_directory: str, config_settings: Optional[Mapping[str, Any]] = None
) -> str:
    """Prepare the metadata, places it in metadata_directory"""
    _patched_meta = None
    if _using_mina_package_structure():
        mina_target: Optional[str] = _get_build_target(config_settings)
        if mina_target is None:
            raise ValueError(
                "detected mina structure enabled but no current package specified to build"
            )
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
    if _using_mina_package_structure():
        mina_target: Optional[str] = _get_build_target(config_settings)
        if mina_target is None:
            raise ValueError(
                "detected mina structure enabled but no current package specified to build"
            )
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
    if _using_mina_package_structure():
        mina_target: Optional[str] = _get_build_target(config_settings)
        if mina_target is None:
            raise ValueError(
                "detected mina structure enabled but no current package specified to build"
            )
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
    if _using_mina_package_structure():
        mina_target: Optional[str] = _get_build_target(config_settings)
        if mina_target is None:
            raise ValueError(
                "detected mina structure enabled but no current package specified to build"
            )
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
    if _using_mina_package_structure():
        mina_target: Optional[str] = _get_build_target(config_settings)
        if mina_target is None:
            raise ValueError(
                "detected mina structure enabled but no current package specified to build"
            )
        if not _has_package(mina_target):
            raise ValueError(f"{mina_target} is not defined as a mina package")
        _patched_meta = _patch_pdm_metadata(mina_target)  # os.chdir may break behavior
    with EditableBuilder(Path.cwd(), config_settings) as builder:
        if _patched_meta is not None:
            builder._meta = _patched_meta
        return Path(builder.build(wheel_directory)).name
