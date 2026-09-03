
from pydantic import BaseModel, Field, model_validator
from typing import Literal
from enum import Enum
from dataclasses import dataclass


# Group 1 : Graph-related pydantic models
class Hub(BaseModel):
    kind: Literal['start_hub', 'hub', 'end_hub']
    name: str
    x: int
    y: int
    zone: Literal['normal', 'restricted',
                  'priority', 'blocked'] = Field(default='normal')
    color: str
    max_drones: int = Field(default=1)

    @model_validator(mode='after')
    def change_color(self) -> 'Hub':
        if self.color == 'rainbow':
            self.color = 'fuchsia'
        return self


class Edge(BaseModel):
    name: str
    hub_a: Hub
    hub_b: Hub
    max_capacity: int = Field(default=1)


class GraphModel(BaseModel):
    nb_agents: int = Field(ge=1)
    hubs: list[Hub]
    edges: list[Edge]

    @model_validator(mode='after')
    def check_edges(self) -> 'GraphModel':
        hub_names = [h.name for h in self.hubs]
        for e in self.edges:
            if e.hub_a.name not in hub_names or e.hub_b.name not in hub_names:
                raise ValueError("Found invalid connection in graph.")
        return self

    @model_validator(mode='after')
    def check_start_end(self) -> 'GraphModel':
        if len([h for h in self.hubs if h.kind == 'start_hub']) != 1:
            raise ValueError("Error building graph - check start_hub")
        if len([h for h in self.hubs if h.kind == 'end_hub']) != 1:
            raise ValueError("Error building graph - check end_hub")
        return self


# Group 2 : Path-finding structs
class ZoneCost(Enum):
    """Mapping of zones with their effective costs."""
    NORM = ("normal", 1)
    PRIOR = ("priority", 1)     # to prioritize, has lower eff cost
    RES = ("restricted", 2)
    BLOCK = ("blocked", None)


@dataclass
class PathStep:
    # to track everything in A*, to be handed to CBS & visualizer
    agent_id: str
    hub_from: Hub
    hub_to: Hub
    t_depart: int
    t_arrive: int   # adds turns
    in_transit: bool = False


@dataclass
class Constraint:
    # passed to A*
    agent_id: str
    position: str
    t: int


@dataclass
class Conflict:
    # detected by CBS
    agent_a: str
    agent_b: str
    position: str   # name of hub/edge
    time: int


@dataclass
class CBSNode:
    constraints: list[Constraint]
    all_paths: dict[str, list[PathStep]]
    cost_per_agent: dict[str, int]


@dataclass
class CBSResult:
    joint_plan: dict[str, list[PathStep]]
    cost_per_agent: dict[str, int]
    makespan: int
    total_cost: int
