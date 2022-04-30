from pdm.core import Core
from pdm.project.config import ConfigItem


def ensure_config(core: Core):
    core.add_config("tool.mina.packages", ConfigItem(description=""))
