
from pydantic import BaseModel, Field, model_validator
from typing import Literal
from enum import Enum
from dataclasses import dataclass


class ParsingError(Exception):
    def __init__(self, msg: str):
        self.msg = msg
        super().__init__(msg)

    def __str__(self) -> str:
        return f"ParsingError: {self.msg}"


# Group 1 : Graph-related pydantic models
class Hub(BaseModel):
    kind: Literal['start_hub', 'hub', 'end_hub']
    name: str
    x: int
    y: int
    zone: Literal['normal', 'restricted',
                  'priority', 'blocked'] = Field(default='normal')
    color: str
    max_drones: int = Field(default=1, ge=1)

    @model_validator(mode='after')
    def check_name(self) -> 'Hub':
        if '-' in self.name or ' ' in self.name:
            raise ValueError("Hub name cannot contain dashes or spaces.")
        return self

    @model_validator(mode='after')
    def change_color(self) -> 'Hub':
        if self.color == 'rainbow':
            self.color = 'fuchsia'
        return self


class Edge(BaseModel):
    name: str
    hub_a: Hub
    hub_b: Hub
    max_capacity: int = Field(default=1, ge=1)


class GraphModel(BaseModel):
    nb_agents: int = Field(ge=1)
    hubs: list[Hub]
    edges: list[Edge]

    @model_validator(mode='after')
    def check_edges(self) -> 'GraphModel':
        hub_names = [h.name for h in self.hubs]
        for e in self.edges:
            if e.hub_a.name not in hub_names or e.hub_b.name not in hub_names:
                raise ValueError(f"Found invalid connection in graph: {e}")
        for e1, e2 in zip(self.edges, self.edges[1:]):
            if set(e1.name.split('-')) == set(e2.name.split('-')):
                raise ValueError(f"Found duplicate connections:\n \
                                 {e1.name} and {e2.name}")
        return self

    @model_validator(mode='after')
    def check_start_end(self) -> 'GraphModel':
        if len([h for h in self.hubs if h.kind == 'start_hub']) != 1:
            raise ValueError("There must be exactly 1 start_hub")
        if len([h for h in self.hubs if h.kind == 'end_hub']) != 1:
            raise ValueError("There must be exactly 1 end_hub")
        return self

    @model_validator(mode='after')
    def check_hub_names(self) -> 'GraphModel':
        if len([h.name for h in self.hubs
                ]) != len(set(h.name for h in self.hubs)):
            raise ValueError("Hubs must have unique names")
        return self

    @model_validator(mode='after')
    def check_start_end_cap(self) -> 'GraphModel':
        for h in self.hubs:
            if h.kind == 'start_hub' or h.kind == 'end_hub':
                h.max_drones = self.nb_agents
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
