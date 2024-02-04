from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from pdm.backend._vendor.packaging.requirements import Requirement
from pdm.backend._vendor.packaging.utils import canonicalize_name
from pdm.backend.config import Config
from pdm.backend.hooks import Context
from pdm.backend.editable import EditableBuilder

if sys.version_info >= (3, 11):
    import tomllib as tomli
else:
    from pdm.backend._vendor import tomli


def _get_build_target(context: Context) -> str | None:
    tool_mina = context.config.data.get("tool", {}).get("mina", {})
    return (
        context.config_settings.get("mina-target")
        or os.environ.get("MINA_BUILD_TARGET")
        or tool_mina.get("default-build-target")
    )


def _using_override(config: Config, package_conf: dict[str, Any]) -> bool:
    if "override" in package_conf:
        return package_conf["override"]
    return config.data.get("tool", {}).get("mina", {}).get("override-global", False)


def _get_mina_packages(context: Context):
    mina_packages = (
        context.config.data.get("tool", {}).get("mina", {}).get("packages", [])
    )
    for i in context.root.glob(".mina/*.toml"):
        name = i.name[:-5]
        if name not in mina_packages:
            mina_packages.append(name)
    return mina_packages

def _patch_package_deps(context: Context, pkg_project: dict[str, Any]) -> None:
    mina_packages = _get_mina_packages(context)
    is_editable = isinstance(context.builder, EditableBuilder)

    deps: list[str] = pkg_project.setdefault("dependencies", [])
    patched_deps: list[str] = []
    deps_map = {canonicalize_name(Requirement(i).name): i for i in deps}
    for name, dep in deps_map.items():
        if name not in mina_packages:
            patched_deps.append(dep)
        elif is_editable:
            # FIXME: 需要一种更完备的方法判定 workspace
            patched_deps.append(f"-e file://${{PROJECT_ROOT}}/#egg={name}")
        else:
            patched_deps.append(dep)

    pkg_project["dependencies"] = patched_deps

    optional_dep_groups: dict[str, list[str]] = pkg_project.setdefault(
        "optional-dependencies", {}
    )
    for group, optional_deps in optional_dep_groups.items():
        optional_deps = {canonicalize_name(Requirement(i).name): i for i in optional_deps}
        patched_optional_deps = []
        for name, dep in optional_deps.items():
            if name not in mina_packages:
                patched_optional_deps.append(dep)
            elif is_editable:
            # FIXME: 需要一种更完备的方法判定 workspace
                patched_optional_deps.append(f"-e file://${{PROJECT_ROOT}}/#egg={name}")
            else:
                patched_optional_deps.append(dep)
        optional_dep_groups[group] = patched_optional_deps
                


def _get_standalone_config(root: Path, pkg: str):
    config_file = root / ".mina" / f"{pkg}.toml"
    if not config_file.exists():
        return

    return tomli.loads(config_file.read_text())


def _update_config(context: Context, config: Config, package: str) -> None:
    package_conf = _get_standalone_config(config.root, package)
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

    package_metadata = package_conf.pop("project", {})
    using_override = _using_override(config, package_conf)
    if not using_override:
        _patch_package_deps(context, package_metadata)

    build_config = config.build_config

    # Override build config
    build_config.update(package_conf)

    if using_override:
        config.data["project"] = package_metadata
    else:
        deep_merge(config.metadata, package_metadata)
        # dependencies are already merged, restore them
        config.metadata["dependencies"] = package_metadata.get("dependencies", [])
        config.metadata["optional-dependencies"] = package_metadata.get(
            "optional-dependencies", {}
        )

    config.validate(config.data, config.root)


def deep_merge(source: MutableMapping, target: Mapping) -> Mapping:
    for key, value in target.items():
        if key in source and isinstance(value, list):
            source[key].extend(value)
        elif key in source and isinstance(value, dict):
            deep_merge(source[key], value)
        else:
            source[key] = value
    return source


def pdm_build_initialize(context: Context) -> None:
    mina_target = _get_build_target(context)
    if mina_target is None:
        return
    _update_config(context, context.config, mina_target)
