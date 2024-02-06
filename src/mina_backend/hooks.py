from __future__ import annotations

from typing import Mapping, MutableMapping

from pdm.backend.hooks import Context

import os
import sys
from pathlib import Path
from typing import Any

from pdm.backend.config import Config
from pdm.backend.hooks import Context

if sys.version_info >= (3, 11):
    import tomllib as tomli
else:
    from pdm.backend._vendor import tomli


def is_mina_enabled(context: Context) -> bool:
    tool_mina = context.config.data.get("tool", {}).get("mina", {})
    return bool(tool_mina.get("enabled"))


def get_build_target(context: Context) -> str | None:
    tool_mina = context.config.data.get("tool", {}).get("mina", {})
    return (
        context.config_settings.get("mina-target")
        or os.environ.get("MINA_BUILD_TARGET")
        or tool_mina.get("default-build-target")
    )


def is_override(config: Config, package_conf: dict[str, Any]) -> bool:
    if "override" in package_conf:
        return package_conf["override"]
    return config.data.get("tool", {}).get("mina", {}).get("override-global", False)


def mina_packages(context: Context) -> list[str]:
    mina_packages = list(
        context.config.data.get("tool", {}).get("mina", {}).get("packages", {}).keys()
    )
    for i in context.root.glob(".mina/*.toml"):
        name = i.stem
        if name not in mina_packages:
            mina_packages.append(name)
    return mina_packages


def get_mina_standalone_config(root: Path, pkg: str):
    config_file = root / ".mina" / f"{pkg}.toml"
    if not config_file.exists():
        return

    return tomli.loads(config_file.read_text())


def get_package_info(context: Context, target: str):
    if not is_mina_enabled(context):
        raise ValueError("Mina is not enabled")

    package_conf = get_mina_standalone_config(context.config.root, target)
    if package_conf is not None:
        package_conf.setdefault("includes", []).append(f".mina/{target}.toml")
    else:
        package_conf = (
            context.config.data.get("tool", {})
            .get("mina", {})
            .get("packages", {})
            .get(target, None)
        )
        if package_conf is None:
            raise ValueError(f"No package named '{target}'")

    return package_conf



def _update_config(context: Context, package: str) -> None:
    package_conf = get_package_info(context, package)

    package_metadata = package_conf.get("project", {})
    using_override = is_override(context.config, package_conf)

    build_config = context.config.build_config

    # Override build config
    build_config.update(package_conf)

    if using_override:
        context.config.data["project"] = package_metadata
    else:
        deep_merge(context.config.metadata, package_metadata)
        # dependencies are already merged, restore them
        context.config.metadata["dependencies"] = package_metadata.get("dependencies", [])
        context.config.metadata["optional-dependencies"] = package_metadata.get(
            "optional-dependencies", {}
        )

    context.config.validate(context.config.data, context.config.root)


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
    if not is_mina_enabled(context):
        return

    mina_target = get_build_target(context)
    if mina_target is None:
        return
    
    _update_config(context, mina_target)
