
from pydantic import BaseModel, Field, model_validator
from typing import Literal
from enum import Enum
from dataclasses import dataclass


class ParsingError(Exception):
    """Error raised when a map file cannot be parsed or validated.

    Args:
        msg: Explanation of the parsing or validation failure.
    """

    def __init__(self, msg: str):
        """Initialize an error with a human-readable message.

        Args:
            msg: Explanation of the parsing or validation failure.

        Returns:
            None.
        """
        self.msg = msg
        super().__init__(msg)

    def __str__(self) -> str:
        """Return the error message with its exception type.

        Returns:
            The formatted parsing error message.
        """
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
    max_drones: int = Field(default=1, ge=1)

    @model_validator(mode='after')
    def check_name(self) -> 'Hub':
        """Ensure the hub name is safe to use in connection identifiers.

        Returns:
            This validated hub.

        Raises:
            ValueError: If the name contains a dash or space.
        """
        if '-' in self.name or ' ' in self.name:
            raise ValueError("Hub name cannot contain dashes or spaces.")
        return self

    @model_validator(mode='after')
    def change_color(self) -> 'Hub':
        """Replace the special rainbow color with a supported color.

        Returns:
            This validated hub.
        """
        if self.color == 'rainbow':
            self.color = 'fuchsia'
        return self


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
    def check_edges(self) -> 'GraphModel':
        """Validate edge endpoints and reject duplicate connections.

        Returns:
            This validated graph.

        Raises:
            ValueError: If an endpoint is unknown or a connection is repeated.
        """
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

    @model_validator(mode='after')
    def check_hub_names(self) -> 'GraphModel':
        """Ensure every hub has a unique name.

        Returns:
            This validated graph.

        Raises:
            ValueError: If two hubs share a name.
        """
        if len([h.name for h in self.hubs
                ]) != len(set(h.name for h in self.hubs)):
            raise ValueError("Hubs must have unique names")
        return self

    @model_validator(mode='after')
    def check_start_end_cap(self) -> 'GraphModel':
        """Allow every drone at the start and end hubs.

        Returns:
            This validated graph.
        """
        for h in self.hubs:
            if h.kind == 'start_hub' or h.kind == 'end_hub':
                h.max_drones = self.nb_agents
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
