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
        cost_per_agent: dict[str, float] = {}
        for agent in self.agent_ids:
            path, path_cost = self.single_agent_path(agent, constraints)
            if not path:
                print(f"WARNING: {agent} found no path under constraints: "
                      f"{[c for c in constraints if c.agent_id == agent]}")
            paths[agent] = path
            cost_per_agent[agent] = path_cost
        return paths, cost_per_agent

    def _detect_conflict(self,
                         joint_plan: dict[str, list[PathStep]]
                         ) -> Conflict | None:
        """Find the first hub-capacity or connection-overlap conflict.
            Args:   joint_plan: Timestamped path for each agent.
            Returns:    The first detected conflict, 
                        or ``None`` when the plan is valid.
        """
        # {<hub.name, timestamp>: [agent_id]}

        makespan = max(steps[-1].t_arrive for steps in joint_plan.values()) if joint_plan else 0
        occupied_hubs: dict[tuple[str, int], list[str]] = {}
        for agent_id, steps in joint_plan.items():
            if not steps:
                continue
            occupied_hubs.setdefault((steps[0].hub_from.name, 0), []).append(agent_id)
            for i, step in enumerate(steps):
                hub_name = step.hub_to.name
                arrival_time = step.t_arrive
                departure_time = steps[i + 1].t_depart if i + 1 < len(steps) else makespan
                
                for t in range(arrival_time, departure_time + 1):
                    agents = occupied_hubs.setdefault((hub_name, t), [])
                    
                    entry = (agent_id, arrival_time)
                    if entry not in agents:
                        agents.append(entry)                

        for (hub_name, t), agents in occupied_hubs.items():
            occupied_hub = self._hub_lookup[hub_name]
            cap = len(self.agent_ids) if occupied_hub.kind in ('start_hub', 'end_hub') else occupied_hub.max_drones
            if len(agents) > cap:
                a1_id, a1_arrive = agents[0]
                a2_id, a2_arrive = agents[1]
                # print(f"HUB CONFLICT: {hub_name} cap={cap} agents={agents} t={t}")
                return Conflict(a1_id, a2_id, hub_name, a2_arrive)
        
        edge_intervals: dict[str, list[tuple[str, int, int]]] = {}
        for agent_id, steps in joint_plan.items():
            for step in steps:
                if step.in_transit:
                    edge_name = Edge.canonical_name(step.hub_from.name, step.hub_to.name)
                    edge_intervals.setdefault(edge_name, []).append(
                            (agent_id, step.t_depart, step.t_arrive))
        # print(f"Edge intervals: {edge_intervals}")
        for e_name, intervals in edge_intervals.items():
            edge = self._edge_lookup[e_name]
            cap = edge.max_capacity

            # Build occupancy map: for each time, which agents use the edge
            time_occupancy: dict[int, list[str]] = {}
            for agent_id, t_depart, t_arrive in intervals:
                for t in range(t_depart, t_arrive):
                    time_occupancy.setdefault(t, []).append((agent_id, t_depart))
            for t, agent_departs in time_occupancy.items():
                if len(agent_departs) > cap:
                    a1_id, a1_dep = agent_departs[-1]
                    a2_id, a2_dep = agent_departs[-2]
                    return Conflict(a1_id, a2_id, e_name, max(a1_dep, a2_dep))
        return None

    # def _count_conflicts(self, joint_plan: dict[str, list[PathStep]]) -> int:
    #     """Count total hub and edge capacity collisions across a joint_plan."""
    #     conflict_count = 0
        
    #     # 1. Count hub capacity excess
    #     makespan = max(steps[-1].t_arrive for steps in joint_plan.values()) if joint_plan else 0
    #     occupied_hubs: dict[tuple[str, int], list[str]] = {}
    #     for agent_id, steps in joint_plan.items():
    #         if not steps:
    #             continue
    #         occupied_hubs.setdefault((steps[0].hub_from.name, 0), []).append(agent_id)
    #         for i, step in enumerate(steps):
    #             hub_name = step.hub_to.name
    #             arrival_time = step.t_arrive
    #             departure_time = steps[i + 1].t_depart if i + 1 < len(steps) else makespan
                
    #             for t in range(arrival_time, departure_time + 1):
    #                 agents = occupied_hubs.setdefault((hub_name, t), [])
    #                 if agent_id not in agents:
    #                     agents.append(agent_id)

    #     for (hub_name, t), agents in occupied_hubs.items():
    #         occupied_hub = self._hub_lookup[hub_name]
    #         cap = len(self.agent_ids) if occupied_hub.kind in ('start_hub', 'end_hub') else occupied_hub.max_drones
    #         if len(agents) > cap:
    #             conflict_count += (len(agents) - cap)
        
    #     # 2. Count edge capacity excess
    #     edge_intervals: dict[str, list[tuple[str, int, int]]] = {}
    #     for agent_id, steps in joint_plan.items():
    #         for step in steps:
    #             if step.in_transit:
    #                 edge_name = Edge.canonical_name(step.hub_from.name, step.hub_to.name)
    #                 edge_intervals.setdefault(edge_name, []).append(
    #                         (agent_id, step.t_depart, step.t_arrive))
                            
    #     for e_name, intervals in edge_intervals.items():
    #         edge = self._edge_lookup[e_name]
    #         cap = edge.max_capacity

    #         time_occupancy: dict[int, list[str]] = {}
    #         for agent_id, t_depart, t_arrive in intervals:
    #             for t in range(t_depart, t_arrive):
    #                 time_occupancy.setdefault(t, []).append(agent_id)
    #         for t, agents_in_edge in time_occupancy.items():
    #             if len(agents_in_edge) > cap:
    #                 conflict_count += (len(agents_in_edge) - cap)

    #     return conflict_count

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
        # changed priority in heapq - to avoid deadlocks
        open_lst: list[tuple[float, int, CBSNode]] = [
            (
                sum(root_cost_pa.values()), 
                next(counter), 
                root
            )
        ]

        for _ in range(1500):
            node_cost, _, node = heapq.heappop(open_lst)
            conflict = self._detect_conflict(node.all_paths)
            
            if not conflict:
                makespan: int = max(
                    steps[-1].t_arrive for steps in node.all_paths.values())
                return CBSResult(node.all_paths,
                                 node.cost_per_agent,
                                 makespan, node_cost)

            else:
                print(f"Iter {_}: cost={node_cost}, constraints={len(node.constraints)}, "
                      f"conflict={conflict.position}@t={conflict.time}, open_lst={len(open_lst)}")
                is_edge = conflict.position in self._edge_lookup
    
                if is_edge:
                    cap = self._edge_lookup[conflict.position].max_capacity
                    agents_at_conflict = [
                        agent for agent, steps in node.all_paths.items()
                        if any(Edge.canonical_name(s.hub_from.name,
                                s.hub_to.name) == conflict.position
                                and s.t_depart <= conflict.time < s.t_arrive
                            for s in steps)
                    ]
                else:
                    hub = self._hub_lookup[conflict.position]
                    cap = (len(self.agent_ids) if hub.kind in ('start_hub', 'end_hub')
                            else (hub.max_drones))
                    agents_at_conflict = [
                        agent for agent, steps in node.all_paths.items()
                        if any(s.hub_to.name == conflict.position
                                and s.t_arrive == conflict.time
                                for s in steps)
                    ]
                # print(f"Conflict: {conflict}")
                # print(f"agents_at_conflict: {agents_at_conflict}")
                if not agents_at_conflict:
                    print(f"Warning: conflict detected but no agents found at {conflict.position} t={conflict.time}")
                    continue
                agents_at_conflict.sort() 
                # Pick exactly 'cap + 1' agents. Since only 'cap' can fit, 
                # at least ONE of these agents MUST be constrained.
                subset_to_branch = agents_at_conflict[:cap + 1]

                for agent in subset_to_branch:
                    agent_arrival = next(
                                    s.t_arrive for s in node.all_paths[agent]
                                    if s.hub_to.name == conflict.position)
                    
                    new_constraints = node.constraints + [
                            Constraint(agent, conflict.position, agent_arrival)
                    ]
                    new_paths, new_cost_pa = self._all_paths(new_constraints)
                    
                    # If this constraint permanently blocks an agent, prune the branch
                    if any(not path for path in new_paths.values()):
                        continue
                    child = CBSNode(new_constraints, new_paths, new_cost_pa)
                    heapq.heappush(
                        open_lst, 
                        (
                            sum(new_cost_pa.values()),
                            next(counter), 
                            child
                        )
                    )

        print("No solution found within iteration limit.")
        return None


if __name__ == "__main__":
    from src.parser import GraphParser
    filename = "maps/medium/02_circular_loop.txt"
    parser = GraphParser(filename)
    solver = CBS(parser._graph)
    res = solver.solve()
    print(res)