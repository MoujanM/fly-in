
from pydantic import BaseModel, Field, model_validator
from typing import Literal
from enum import Enum
from dataclasses import dataclass


class ParsingError(Exception):
    """Error raised when a map file cannot be parsed or validated."""

    def __init__(self, msg: str):
        """Initialize error with a human-readable message."""
        self.msg = msg
        super().__init__(msg)

    def __str__(self) -> str:
        """Return the error message with its exception type."""
        return f"ParsingError: {self.msg}"


# Group 1 : Graph-related pydantic models
class Hub(BaseModel):
    """A graph location where drones can wait or change direction.

    Attributes:
        kind: Whether the hub is the start, an intermediate hub, or the goal.
        name: Unique identifier used in map connections and constraints.
        x: Horizontal logical coordinate.
        y: Vertical logical coordinate.
        zone: Movement-cost category for the hub.
        color: Color used by the visualizer.
        max_drones: Maximum number of drones allowed at the hub.
    """

    kind: Literal['start_hub', 'hub', 'end_hub']
    name: str
    x: int
    y: int
    zone: Literal['normal', 'restricted',
                  'priority', 'blocked'] = Field(default='normal')
    color: str
    max_drones: int | None

    # @model_validator(mode='after')
    # def check_name(self) -> 'Hub':
    #     """Ensure the hub name is safe to use in connection identifiers."""
    #     if '-' in self.name or ' ' in self.name:
    #         raise ValueError("Hub name cannot contain dashes or spaces.")
    #     return self


class Edge(BaseModel):
    """A bidirectional connection between two hubs.

    Attributes:
        name: Connection identifier composed from its endpoint names.
        hub_a: First endpoint of the connection.
        hub_b: Second endpoint of the connection.
        max_capacity: Maximum number of drones using the connection.
    """

    name: str
    hub_a: Hub
    hub_b: Hub
    max_capacity: int = Field(default=1, ge=1)


class GraphModel(BaseModel):
    """Validated graph and drone count used by the routing algorithms.

    Attributes:
        nb_agents: Number of drones to route.
        hubs: Locations in the graph.
        edges: Connections between locations.
    """

    nb_agents: int = Field(ge=1)
    hubs: list[Hub]
    edges: list[Edge]

    @model_validator(mode='after')
    def check_start_end(self) -> 'GraphModel':
        """Require exactly one start hub and one end hub.

        Returns:
            This validated graph.

        Raises:
            ValueError: If the graph does not have one start and one end hub.
        """
        if len([h for h in self.hubs if h.kind == 'start_hub']) != 1:
            raise ValueError("There must be exactly 1 start_hub")
        if len([h for h in self.hubs if h.kind == 'end_hub']) != 1:
            raise ValueError("There must be exactly 1 end_hub")
        return self

    # @model_validator(mode='after')
    # def check_start_end_cap(self) -> 'GraphModel':
    #     for h in self.hubs:
    #         if h.kind in ('start_hub', 'end_hub'):
    #             object.__setattr__(h, 'max_drones', self.nb_agents)
    #     return self

    @model_validator(mode='after')
    def check_no_isolated_hubs(self) -> 'GraphModel':
        connected_names: set[str] = set()
        for e in self.edges:
            connected_names.add(e.hub_a.name)
            connected_names.add(e.hub_b.name)
        for h in self.hubs:
            if h.name not in connected_names:
                raise ValueError(
                    f"Hub '{h.name}' has no connections — "
                    f"Input graph is disconnected."
                )
        return self


# Group 2 : Path-finding structs
class ZoneCost(Enum):
    """Map each hub zone to its effective movement cost.

    A ``None`` cost marks a blocked zone that cannot be entered.
    """
    NORM = ("normal", 1)
    PRIOR = ("priority", 1)     # to prioritize, has lower eff cost
    RES = ("restricted", 2)
    BLOCK = ("blocked", None)


@dataclass
class PathStep:
    """One agent movement or wait action in the time-expanded graph.

    Attributes:
        agent_id: Identifier of the drone taking the step.
        hub_from: Starting hub.
        hub_to: Destination hub.
        t_depart: Turn when the action starts.
        t_arrive: Turn when the action ends.
        in_transit: Whether the drone occupies a connection during the step.
    """

    agent_id: str
    hub_from: Hub
    hub_to: Hub
    t_depart: int
    t_arrive: int   # adds turns
    in_transit: bool = False


@dataclass
class Constraint:
    """Position and time that a specific agent must avoid.

    Attributes:
        agent_id: Identifier of the constrained drone.
        position: Hub or connection name that is unavailable.
        t: Turn at which the position is unavailable.
    """

    agent_id: str
    position: str
    t: int


@dataclass
class Conflict:
    """Collision detected between two agents in a joint plan.

    Attributes:
        agent_a: Identifier of the first conflicting drone.
        agent_b: Identifier of the second conflicting drone.
        position: Hub or connection where the conflict occurs.
        time: Turn at which the conflict occurs.
    """

    agent_a: str
    agent_b: str
    position: str   # name of hub/edge
    time: int


@dataclass
class CBSNode:
    """One node in the Conflict-Based Search constraint tree.

    Attributes:
        constraints: Constraints accumulated along this branch.
        all_paths: Current path for each agent.
        cost_per_agent: Cost of each agent's current path.
    """

    constraints: list[Constraint]
    all_paths: dict[str, list[PathStep]]
    cost_per_agent: dict[str, int]


@dataclass
class CBSResult:
    """Conflict-free plan and aggregate costs returned by CBS.

    Attributes:
        joint_plan: Time-stamped path for every agent.
        cost_per_agent: Movement cost for every agent.
        makespan: Final arrival turn across all agents.
        total_cost: Sum of all individual path costs.
    """

    joint_plan: dict[str, list[PathStep]]
    cost_per_agent: dict[str, int]
    makespan: int
    total_cost: int
