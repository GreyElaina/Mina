from __future__ import annotations
import functools
import os
from pathlib import Path
from pdm.models.candidates import PreparedCandidate
from pdm.builders import EditableBuilder, WheelBuilder
from pdm import termui

from mina.workflow.req import ConfigIncludedRequirement

#@functools.wraps(PreparedCandidate.build)
def patched_build(self: PreparedCandidate) -> Path:
    print("?", self.req)
    """Call PEP 517 build hook to build the candidate into a wheel"""
    self.obtain(allow_all=False)
    if self.wheel:
        return self.wheel
    if not self.req.editable:
        cached = self._get_cached_wheel()
        if cached:
            self.wheel = cached
            return self.wheel
    assert self._source_dir, "Source directory isn't ready yet"
    builder_cls = EditableBuilder if self.req.editable else WheelBuilder
    builder = builder_cls(str(self._unpacked_dir), self.environment)
    build_dir = self._get_wheel_dir()
    os.makedirs(build_dir, exist_ok=True)
    termui.logger.info("Running PEP 517 backend to build a wheel for %s", self.link)
    self.reporter.report_build_start(self.link.filename)  # type: ignore[union-attr]
    if isinstance(self.candidate.req, ConfigIncludedRequirement):
        print("what happened?")
        config_settings = self.candidate.req.config_settings
    else:
        config_settings = {}
    self.wheel = Path(
        builder.build(
            build_dir,
            config_settings=config_settings,
            metadata_directory=self._metadata_dir,
        )
    )
    self.reporter.report_build_end(self.link.filename)  # type: ignore[union-attr]
    return self.wheel


PreparedCandidate.build = patched_build
