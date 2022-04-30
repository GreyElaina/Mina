from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Package:
    name: str
    dependencies: List[str]
    version: str
    description: Optional[str] = None
    readme: Optional[str] = None
    license: Optional[str] = None
