
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

    @staticmethod
    def canonical_name(hub1_name: str, hub2_name: str) -> str:
        """Return a deterministic edge identifier regardless of traversal direction."""
        u, v = sorted([hub1_name, hub2_name])
        return f"{u}-{v}"
        
    @model_validator(mode='after')
    def set_canonical_name(self) -> 'Edge':
        """Ensure the Edge name attribute is always canonicalized upon creation."""
        self.name = self.canonical_name(self.hub_a.name, self.hub_b.name)
        return self


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
        """Check there are exactly one start hub and one end hub."""
        if len([h for h in self.hubs if h.kind == 'start_hub']) != 1:
            raise ValueError("There must be exactly 1 start_hub")
        if len([h for h in self.hubs if h.kind == 'end_hub']) != 1:
            raise ValueError("There must be exactly 1 end_hub")
        return self

    @model_validator(mode='after')
    def check_start_end_cap(self) -> 'GraphModel':
        for h in self.hubs:
            if h.kind in ('start_hub', 'end_hub'):
                object.__setattr__(h, 'max_drones', self.nb_agents)
        return self

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

    @model_validator(mode='after')
    def check_graph_connectivity(self) -> 'GraphModel':
        """Ensure the entire graph is connected using Union-Find.
        Raises:
            ValueError: If the graph contains unreachable components.
        """
        if len(self.hubs) <= 1:
            return self
    
        # Union-Find data structure
        parent: dict[str, str] = {h.name: h.name for h in self.hubs}
    
        def find(hub_name: str) -> str:
            """Find the root of a hub's component."""
            if parent[hub_name] != hub_name:
                parent[hub_name] = find(parent[hub_name])  # path compression
            return parent[hub_name]
    
        def union(hub1: str, hub2: str) -> None:
            """Unite two hubs into the same component."""
            root1, root2 = find(hub1), find(hub2)
            if root1 != root2:
                parent[root1] = root2
            return None
    
        # Union all connected hubs via edges
        for edge in self.edges:
            union(edge.hub_a.name, edge.hub_b.name)
    
        # Check if all hubs belong to the same component
        start = next(h.name for h in self.hubs if h.kind == "start_hub")
        end = next(h.name for h in self.hubs if h.kind == "end_hub")
        if find(start) != find(end):
            raise ValueError(
                f"end_hub {end} not reachable from"
                f" start_hub {start} - Graph is disconnected"
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
    cost_per_agent: dict[str, float]


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
    cost_per_agent: dict[str, float]
    makespan: int
    total_cost: int
