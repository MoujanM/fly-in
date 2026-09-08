from src.singlepath import PathFinder
from src.models import Conflict, Constraint, CBSNode, CBSResult, PathStep
from src.models import Hub, Edge, GraphModel
import heapq
import itertools


class CBS(PathFinder):
    """
    Inherits specs and single-agent path-finder from parent.
    Includes Conflict-Based Search (CBS) algorithm which includes
    a two-layered search:
        - high-level; searches a global constraints tree
        - low-level; searches paths for individual agents (parent class)
    """
    def __init__(self, puzzle: GraphModel):
        """Initialize CBS lookup tables for a validated graph.

        Args:
            puzzle: Graph to route all agents through.

        Returns:
            None.
        """
        super().__init__(puzzle)
        self._hub_lookup: dict[str, Hub] = {h.name: h for h in self.hubs}
        self._edge_lookup: dict[str, Edge] = {e.name: e for e in self.edges}

    def _all_paths(self,
                   constraints: list[Constraint]) -> tuple[
                       dict[str, list[PathStep]],
                       dict[str, int]]:
        """Find paths for every agent under a shared constraint set.

        Args:
            constraints: Hub or connection reservations to apply to the search.

        Returns:
            A tuple containing each agent's path and its movement cost.
        """

        paths: dict[str, list[PathStep]] = {}
        cost_per_agent: dict[str, int] = {}
        for agent in self.agent_ids:
            path, path_cost = self.single_agent_path(agent, constraints)
            paths[agent] = path
            cost_per_agent[agent] = path_cost
        return paths, cost_per_agent

    def _detect_conflict(self,
                         joint_plan: dict[str, list[PathStep]]
                         ) -> Conflict | None:
        """Find the first hub-capacity or connection-overlap conflict.

        Args:
            joint_plan: Timestamped path for each agent.

        Returns:
            The first detected conflict, or ``None`` when the plan is valid.
        """
        # {<hub.name, timestamp>: [agent_id]}
        occupied_hubs: dict[tuple[str, int], list[str]] = {}
        for agent_id, steps in joint_plan.items():
            for step in steps:
                occupied_hubs.setdefault(
                    (step.hub_to.name, step.t_arrive), []).append(agent_id)

        # now scan for conflict
        for (hub_name, t), agents in occupied_hubs.items():
            occupied_hub = self._hub_lookup[hub_name]
            cap = (occupied_hub.max_drones if
                   occupied_hub.max_drones is not None else 1)
            if len(agents) > cap:
                # conflict identified !
                return Conflict(agent_a=agents[0],
                                agent_b=agents[1],
                                position=occupied_hub.name,
                                time=t)

        edge_intervals: dict[str, list[tuple[str, int, int]]] = {}
        for agent_id, steps in joint_plan.items():
            for step in steps:
                if step.in_transit:
                    edge_name = f"{step.hub_from.name}-{step.hub_to.name}"
                    edge_intervals.setdefault(edge_name, []).append(
                        (agent_id, step.t_depart, step.t_arrive))

        for e_name, intervals in edge_intervals.items():
            for i, (agent_a, start_a, end_a) in enumerate(intervals):
                for agent_b, start_b, end_b in intervals[i + 1:]:
                    if start_a < end_b and start_b < end_a:
                        # overlap detected
                        return Conflict(agent_a, agent_b, e_name, start_b)
        return None

    def solve(self) -> CBSResult | None:
        """Search for a minimum-cost conflict-free plan.

        Returns:
            A conflict-free result, or ``None`` if the iteration limit is
            reached without finding a solution.
        """
        root_paths, root_cost_pa = self._all_paths([])
        root: CBSNode = CBSNode(
            constraints=[],
            all_paths=root_paths,
            cost_per_agent=root_cost_pa)
        counter = itertools.count()
        open_lst: list[tuple[int, int, CBSNode]] = [
            (sum(root_cost_pa.values()), next(counter), root)
            ]
        for _ in range(100):
            node_cost, _, node = heapq.heappop(open_lst)
            conflict = self._detect_conflict(node.all_paths)
            makespan: int = max(
                steps[-1].t_arrive for steps in node.all_paths.values())
            if not conflict:
                return CBSResult(node.all_paths,
                                 node.cost_per_agent,
                                 makespan, node_cost)

            is_edge: bool = '-' in conflict.position
            if is_edge:
                conflicting_agents = [
                    agent for agent, step in node.all_paths.items()
                    if any(f"{s.hub_from.name}-{s.hub_to.name}" ==
                           conflict.position and
                           s.t_depart == conflict.time for s in step)]
                cap = 0
            else:
                occupied_hub: Hub = self._hub_lookup[conflict.position]
                cap = occupied_hub.max_drones
                conflicting_agents = [
                    agent for agent, step in node.all_paths.items()
                    if any(s.hub_to.name == conflict.position
                           and s.t_arrive == conflict.time
                           for s in step)
                ]
            excess_agents = conflicting_agents[cap:]
            new_constraints = node.constraints + [
                Constraint(agent, conflict.position, conflict.time)
                for agent in excess_agents]
            new_paths, new_cost_pa = self._all_paths(new_constraints)
            child = CBSNode(constraints=new_constraints,
                            all_paths=new_paths,
                            cost_per_agent=new_cost_pa)
            heapq.heappush(open_lst, (sum(new_cost_pa.values()),
                                      next(counter), child))
        else:
            print("No solution found within iteration limit.")
            return None
