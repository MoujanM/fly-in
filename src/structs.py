
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Zones(Enum):
    """Mapping of zones with their costs."""
    RES = ("restricted", 2)
    NORM = ("normal", 1)
    PRIOR = ("priority", 1)
    BLOCK = "blocked"


class Colours(Enum):
    """Optional, for visual representations."""
    pass


@dataclass
class Hub:
    kind: str
    name: str
    x: int
    y: int
    zone: str | None
    color: str | None
    max_drones: int


@dataclass
class Edge:
    hub_a: Hub
    hub_b: Hub
    max_capacity: int
