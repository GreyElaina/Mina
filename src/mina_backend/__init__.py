from typing import Any

from pdm import backend

# Expose the backend APIs from pdm.backend
__all__ = [
    "get_requires_for_build_wheel",
    "get_requires_for_build_sdist",
    "get_requires_for_build_editable",
    "prepare_metadata_for_build_wheel",
    "prepare_metadata_for_build_editable",
    "build_wheel",
    "build_sdist",
    "build_editable",
]


def __getattr__(name: str) -> Any:
    return getattr(backend, name)
