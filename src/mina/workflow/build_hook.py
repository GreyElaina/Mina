from __future__ import annotations

from pdm.models.requirements import Requirement
from pdm.cli.hooks import HookManager
from pdm.signals import pre_lock
from pdm.project import Project
from mina.workflow.req import ConfigIncludedRequirement
from mina.workflow.utils import is_mina_enabled, mina_packages, get_package_info
import mina.workflow.patched  # noqa: F401

@pre_lock.connect
def pdm_pre_lock(project: Project, hooks: HookManager, requirements: list[Requirement], dry_run: bool):
    if not is_mina_enabled(project):
        return

    packages: dict[str, str] = {
        get_package_info(project, i)["project"]["name"]: i
        for i in mina_packages(project)
    }
    for index, req in enumerate(requirements):
        if req.project_name in packages:
            requirements[index] = ConfigIncludedRequirement(
                url=f"file://{project.root.absolute()}/#egg={req.name}",
                path=project.root.absolute(),
                marker=req.marker,
                extras=req.extras,
                specifier=req.specifier,
                editable=True,
                prerelease=req.prerelease,
                groups=req.groups,
                config_settings={"mina-target": packages[req.project_name]},
            )
            requirements[index].name = req.name
    
    #print(requirements)