from __future__ import annotations

from pdm.models.requirements import FileRequirement
from dataclasses import dataclass, field


@dataclass(eq=False)
class ConfigIncludedRequirement(FileRequirement):
    config_settings: dict[str, str] = field(default_factory=dict)

    def _hash_key(self) -> tuple:
        return super()._hash_key() + (tuple(self.config_settings.items()),)

    def _check_installable(self) -> None:
        return