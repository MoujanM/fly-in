from src.singlepath import PathFinder
from src.models import Conflict, Constraint, CBSNode, CBSResult, PathStep
from src.models import Hub, Edge, GraphModel
import heapq
import itertools


class CBS(PathFinder):
    """
    Inherits specs and single-agent path-finder from parent.
    Includes Conflict-Based Search (CBS) algorithm with
    a two-layered search:
         - high-level; searches a global constraints tree
         - low-level; searches paths for individual agents (parent class)
    """
    
    def __init__(self, puzzle: GraphModel) -> None:
        """Initialize CBS lookup tables for a validated graph."""
        super().__init__(puzzle)
        self._hub_lookup: dict[str, Hub] = {h.name: h for h in self.hubs}
        self._edge_lookup: dict[str, Edge] = {e.name: e for e in self.edges}

    def _all_paths(self,
                   constraints: list[Constraint]) -> tuple[
                       dict[str, list[PathStep]],
                       dict[str, float]]:
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

    def _build_hub_occupancy(self, 
                             joint_plan: dict[str, list[PathStep]]
                             ) -> dict[tuple[str, int], list[str]]:
        """Build a map of (hub_name, time) -> [agent_ids occupying at that time].
        
        Crucially, this tracks occupancy intervals correctly:
        - agent occupies a hub from arrival time through departure time (inclusive)
        - this includes waiting periods, not just arrival moments
        
        Args:
            joint_plan: Path for each agent.
            
        Returns:
            Dict mapping (hub_name, time) to list of agent IDs present then.
        """
        occupancy: dict[tuple[str, int], list[str]] = {}
        
        for agent_id, steps in joint_plan.items():
            if not steps:
                continue
            
            # Agent starts at the start hub at time 0
            occupancy.setdefault((steps[0].hub_from.name, 0), []).append(agent_id)
            
            # For each step, track occupancy from arrival through departure
            for i, step in enumerate(steps):
                hub_name = step.hub_to.name
                t_arrive = step.t_arrive
                # When does the agent leave this hub?
                # Either at the next step's departure time, or end of plan
                if i + 1 < len(steps):
                    t_depart = steps[i + 1].t_depart
                if i + 1 == len(steps):
                    occupancy.setdefault((hub_name, t_arrive), []).append(agent_id)
                else:
                    # Agent stays at final hub indefinitely (goal reached)
                    t_depart = t_arrive
                
                # Mark occupancy for all time steps the agent is at this hub
                # Range is [t_arrive, t_depart] inclusive
                for t in range(t_arrive, t_depart):
                    occupancy.setdefault((hub_name, t), []).append(agent_id)
        return occupancy

    def _detect_conflict(self,
                         joint_plan: dict[str, list[PathStep]]
                         ) -> Conflict | None:
        """Find the first hub-capacity or connection-overlap conflict.
        
        Args:
            joint_plan: Timestamped path for each agent.
            
        Returns:
            The first detected conflict (position and time), or None if valid.
        """
        
        # === Check hub capacity conflicts ===
        hub_occupancy = self._build_hub_occupancy(joint_plan)
        
        for (hub_name, t), agents in hub_occupancy.items():
            occupied_hub = self._hub_lookup[hub_name]
            cap = (len(self.agent_ids) 
                   if occupied_hub.kind in ('start_hub', 'end_hub') 
                   else occupied_hub.max_drones)
            
            if len(agents) > cap:
                # Conflict: too many agents at this hub at this time
                return Conflict(agents[0], agents[1], hub_name, t)
        
        # === Check edge capacity conflicts ===
        # Edges are only used during restricted-zone traversal (in_transit=True)
        edge_occupancy: dict[str, list[tuple[str, int, int]]] = {}
        
        for agent_id, steps in joint_plan.items():
            for step in steps:
                if step.in_transit:
                    # This agent traverses an edge from t_depart to t_arrive
                    edge_name = Edge.canonical_name(step.hub_from.name, step.hub_to.name)
                    edge_occupancy.setdefault(edge_name, []).append(
                        (agent_id, step.t_depart, step.t_arrive)
                    )
        
        # Check each edge for time-interval overlaps
        for edge_name, intervals in edge_occupancy.items():
            edge = self._edge_lookup[edge_name]
            cap = edge.max_capacity
            
            # Build time-indexed occupancy for this edge
            time_occupancy: dict[int, list[str]] = {}
            for agent_id, t_depart, t_arrive in intervals:
                # Agent occupies edge during [t_depart, t_arrive)
                for t in range(t_depart, t_arrive):
                    time_occupancy.setdefault(t, []).append(agent_id)
            
            # Check capacity at each time
            for t, agents in time_occupancy.items():
                if len(agents) > cap:
                    return Conflict(agents[0], agents[1], edge_name, t)
        
        return None

    def solve(self) -> CBSResult | None:
        """Search for a minimum-cost conflict-free plan using CBS.
        
        The algorithm:
        1. Generate a plan for all agents without constraints
        2. Check for conflicts (hub capacity or edge traversal overlap)
        3. If no conflicts, return the plan
        4. Otherwise, pick one conflicting agent and add a constraint
           forbidding it from being at the conflict location at conflict time
        5. Replan only that agent under the new constraint
        6. Push the new node to the queue and repeat
        
        Returns:
            A conflict-free result, or None if iteration limit is reached.
        """
        
        # === Initialize: root node with no constraints ===
        root_paths, root_cost_pa = self._all_paths([])
        root = CBSNode(
            constraints=[],
            all_paths=root_paths,
            cost_per_agent=root_cost_pa
        )
        
        counter = itertools.count()
        open_list: list[tuple[float, int, CBSNode]] = [
            (sum(root_cost_pa.values()), next(counter), root)
        ]
        
        # === Main loop ===
        for iteration in range(1000):
            if not open_list:
                print("CBS exhausted all feasible constraint branches.")
                return None
            # Get the cheapest node from the priority queue
            node_cost, _, node = heapq.heappop(open_list)
            
            # Check for conflicts in this node's plan
            conflict = self._detect_conflict(node.all_paths)
            
            if not conflict:
                # No conflicts! This is a valid solution.
                makespan = max(
                    steps[-1].t_arrive for steps in node.all_paths.values()
                ) if node.all_paths else 0
                return CBSResult(
                    node.all_paths,
                    node.cost_per_agent,
                    makespan,
                    node_cost
                )
            
            # === Conflict detected: branch ===
            # print(f"Iter {iteration}: cost={node_cost}, constraints={len(node.constraints)}, "
            #       f"conflict={conflict.position}@t={conflict.time}, open_list={len(open_list)}")
            
            # Determine whether conflict is at a hub or edge
            is_edge = conflict.position in self._edge_lookup
            
            if is_edge:
                # === Edge conflict ===
                cap = self._edge_lookup[conflict.position].max_capacity
                
                # Find all agents using this edge at conflict.time
                agents_at_conflict = []
                for agent, steps in node.all_paths.items():
                    for step in steps:
                        if (step.in_transit and
                            Edge.canonical_name(step.hub_from.name, step.hub_to.name) == conflict.position and
                            step.t_depart <= conflict.time < step.t_arrive):
                            agents_at_conflict.append(agent)
                            break  # Found this agent, move to next
            
            else:
                # === Hub conflict ===
                hub = self._hub_lookup[conflict.position]
                cap = (len(self.agent_ids) 
                       if hub.kind in ('start_hub', 'end_hub') 
                       else hub.max_drones)
                
                # Find all agents occupying this hub at conflict.time
                # This includes both arrivals AND waiting periods
                agents_at_conflict = []
                for agent, steps in node.all_paths.items():
                    for i, step in enumerate(steps):
                        if step.hub_to.name == conflict.position:
                            # When does this agent leave the hub?
                            if i + 1 < len(steps):
                                t_depart = steps[i + 1].t_depart
                            else:
                                t_depart = step.t_arrive
                            
                            # Is agent present at conflict.time?
                            if step.t_arrive <= conflict.time <= t_depart:
                                agents_at_conflict.append(agent)
                                break  # Found this agent, move to next
            
            if not agents_at_conflict:
                print(f"WARNING: conflict detected but no agents found at "
                      f"{conflict.position} t={conflict.time}")
                continue
            
            agents_at_conflict.sort()
            
            # === Branch: constrain up to (cap + 1) agents ===
            # At least ONE of these (cap + 1) agents must be constrained
            # to resolve the capacity violation
            subset_to_branch = agents_at_conflict[:cap + 1]
            
            for agent in subset_to_branch:
                new_constraint = Constraint(
                                    agent,
                                    conflict.position,
                                    conflict.time,
                )

                # Avoid generating an identical child
            if new_constraint in node.constraints:
                continue

            new_constraints = node.constraints + [new_constraint]
            new_paths, new_cost_pa = self._all_paths(new_constraints)

            if any(not path for path in new_paths.values()):
                continue

            child = CBSNode(
                    constraints=new_constraints,
                    all_paths=new_paths,
                    cost_per_agent=new_cost_pa,
            )

            heapq.heappush(open_list, (
                            sum(new_cost_pa.values()),
                            next(counter),
                            child,
                        ),
            )
                

        print("No solution found within iteration limit.")
        return None


if __name__ == "__main__":
    from src.parser import GraphParser
    filename = "maps/challenger/01_the_impossible_dream.txt"
    parser = GraphParser(filename)
    solver = CBS(parser._graph)
    # root_paths, root_costs = solver._all_paths([])
    # print("ROOT PLAN (no constraints):")
    # for agent, path in root_paths.items():
    #     print(f"\n{agent}: cost={root_costs[agent]}")
    #     for i, step in enumerate(path):
    #         print(f"  {i}: {step.hub_from.name}(t={step.t_depart}) → {step.hub_to.name}(t={step.t_arrive})")
    res = solver.solve()
    if res:
        print(f"\nSolution found!")
        print(f"Makespan: {res.makespan}")
        print(f"Total cost: {res.total_cost}")
        for agent, cost in res.cost_per_agent.items():
            print(f"  {agent}: {cost}")
    else:
        print("No solution found.")