
from pydantic import BaseModel, Field, model_validator
from typing import Literal
from enum import Enum


class Zones(Enum):
    """Mapping of zones with their costs."""
    RES = ("restricted", 2)
    NORM = ("normal", 1)
    PRIOR = ("priority", 1)
    BLOCK = "blocked"


class Hub(BaseModel):
    kind: Literal['start_hub', 'hub', 'end_hub']
    name: str
    x: int
    y: int
    zone: Literal['normal', 'restricted', 'priority', 'blocked'] | None = Field(
        default='normal'
    )
    color: str | None = Field(default=None)
    max_drones: int | None = Field(ge=1, default=1)


class Edge(BaseModel):
    hub_a: Hub
    hub_b: Hub
    max_capacity: int | None = Field(ge=1, default=1)


class GraphModel(BaseModel):
    nb_agents: int = Field(ge=1)
    hubs: list[Hub] = Field()
    edges: list[Edge]

    @model_validator(mode='after')
    def check_edges(self) -> 'GraphModel':
        for e in self.edges:
            if e.hub_a not in self.hubs or e.hub_b not in self.hubs:
                raise ValueError("Found invalid connection in graph.")
        return self
