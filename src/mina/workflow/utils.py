from __future__ import annotations
from pathlib import Path

from pdm.project import Project

import sys
if sys.version_info >= (3, 11):
    import tomllib as tomli
else:
    from pdm.backend._vendor import tomli


def is_mina_enabled(project: Project) -> bool:
    tool_mina = project.pyproject._data.get("tool", {}).get("mina", {})
    return bool(tool_mina.get("enabled"))



def mina_packages(project: Project) -> list[str]:
    mina_packages = list(
        project.pyproject._data.get("tool", {}).get("mina", {}).get("packages", {}).keys()
    )
    for i in project.root.glob(".mina/*.toml"):
        name = i.stem
        if name not in mina_packages:
            mina_packages.append(name)
    return mina_packages



def get_mina_standalone_config(root: Path, pkg: str):
    config_file = root / ".mina" / f"{pkg}.toml"
    if not config_file.exists():
        return

    return tomli.loads(config_file.read_text())



def get_package_info(project: Project, target: str):
    package_conf = get_mina_standalone_config(project.root, target)
    if package_conf is not None:
        package_conf.setdefault("includes", []).append(f".mina/{target}.toml")
    else:
        package_conf = (
            project.pyproject._data.get("tool", {})
            .get("mina", {})
            .get("packages", {})
            .get(target, None)
        )
        if package_conf is None:
            raise ValueError(f"No package named '{target}'")

    return package_conf
