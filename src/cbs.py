from src.singlepath import PathFinder
from src.models import ZoneCost, Conflict, Constraint, CBSNode, CBSResult, PathStep
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
        super().__init__(puzzle)
        self._hub_lookup: dict[str, Hub] = {h.name: h for h in self.hubs}
        self._edge_lookup: dict[str, Edge] = {e.name: e for e in self.edges}

    def _all_paths(self, constraints: list[Constraint]) -> tuple[dict[str, list[PathStep]],
                                                                 dict[str, int],
                                                                 dict[str, list[tuple[str, int, int]]]]:
        """
        Function to call single agent path-finder for all the agents in the map.
        Takes a list of constraints and returns a tuple of two dicts:
            - dict of agent_id and corresponding time-stamped paths
            - dict of agent_id and corresponding path movement cost.
        """

        paths: dict[str, list[PathStep]] = {}
        cost_per_agent: dict[str, int] = {}
        edge_occupancy: dict[str, list[tuple[str, int, int]]] = {}
        for agent in self.agent_ids:
            path, path_cost, edge_watch = self.single_agent_path(agent, constraints)
            paths[agent] = path
            cost_per_agent[agent] = path_cost
            if edge_watch:
                for edge in edge_watch.keys():
                    edge_occupancy.setdefault(edge, []).append(edge_watch[edge])

        return paths, cost_per_agent, edge_occupancy

    def _detect_conflict(self, joint_plan: dict[str, list[PathStep]],
                         edge_occupancy: dict[str, list[tuple[str, int, int]]]) -> Conflict | None:
        """
        Function takes complete joint plan for all agents and merged edge occupancy map
        and builds list of constraints.
        For each timestamp, counts the occupancy of each hub.
        If the count exceeds hub's max_drones, that is a conflict detected.
        Returns a list of constraints as <id, hub, timestamp>.
        """
        # {<hub.name, timestamp>: [agent_id]}
        occupied_hubs: dict[tuple[str, int], list[str]] = {}
        for agent_id, steps in joint_plan.items():
            for step in steps:
                occupied_hubs.setdefault((step.hub_to.name, step.t_arrive), []).append(agent_id)

        # now we have inverted joint_plan, can scan for conflict
        for (hub_name, t), agents in occupied_hubs.items():
            occupied_hub = self._hub_lookup[hub_name]
            if len(agents) > occupied_hub.max_drones:
                # conflict identified !
                return Conflict(agent_a=agents[occupied_hub.max_drones - 1],
                                agent_b=agents[occupied_hub.max_drones],
                                position=occupied_hub.name,
                                time=t)

        # edge conflict - have dict of edge-name: list of (agent_id, t_start, t_end)
        #  for each edge, do any two entries in that list overlap in time?
        # And if so, does that overlap exceed max_link_capacity?
        for edge_name, occupancy_list in edge_occupancy.items():
            edge = self._edge_lookup.get(edge_name)
            for i, (agent_a, t_start_a, t_end_a) in enumerate(occupancy_list):
                for agent_b, t_start_b, t_end_b in occupancy_list[i + 1:]:
                    # detect overlap in time
                    if t_start_a < t_end_b and t_start_b < t_end_a:
                        if edge.max_capacity < 2:
                            return Conflict(
                                agent_a, agent_b, edge_name, t_end_b
                            )
        return None

    def solve(self) -> CBSResult | None:
        # orchestrator - actual implementation

        root_paths, root_cost_pa, root_edge_occ = self._all_paths([])
        root: CBSNode = CBSNode(
            constraints=[],
            all_paths=root_paths,
            cost_per_agent=root_cost_pa,
            edge_occ=root_edge_occ)

        counter = itertools.count()
        open_lst: list[tuple[int, int, CBSNode]] = [(sum(root_cost_pa.values()), next(counter), root)]

        for _ in range(100):
            node_cost, _, node = heapq.heappop(open_lst)
            conflict = self._detect_conflict(node.all_paths, node.edge_occ)

            makespan: int = max(steps[-1].t_arrive for steps in node.all_paths.values())
            
            if not conflict:
                return CBSResult(node.all_paths, node.cost_per_agent, makespan, node_cost)
            
            for agent in (conflict.agent_a, conflict.agent_b):
                constraints = node.constraints + [Constraint(agent, conflict.position, conflict.time)]
                new_paths, new_cost_pa, new_edge_occ = self._all_paths(constraints)
                child = CBSNode(constraints=constraints,
                                all_paths=new_paths,
                                cost_per_agent=new_cost_pa,
                                edge_occ=new_edge_occ)
                heapq.heappush(open_lst, (sum(new_cost_pa.values()), next(counter), child))
        else:
            print("No solution found within iteration limit.")
            return None

    def get_turn_desc(self, result: CBSResult) -> list[str]:
        delivered: set[str] = set()
        turn_map: dict[int, list[PathStep]] = {}
        simualation: list[str] = []

        for agent, path in result.joint_plan.items():
            for step in path:
                turn_map.setdefault(step.t_depart, []).append(step)
        
        for turn in sorted(turn_map.keys()):
            moves = []
            for step in turn_map[turn]:
                if step.agent_id in delivered:
                    continue
                if step.hub_from == step.hub_to:
                    continue
                if step.in_transit:
                    connection: str = f"{step.hub_from.name}-{step.hub_to.name}"
                    moves.append(f"{step.agent_id}-{connection}")
                else:
                    moves.append(f"{step.agent_id}-{step.hub_to.name}")
                if step.hub_to.name == "goal" and not step.in_transit:
                    delivered.add(step.agent_id)
            if moves:
                simualation.append(" ".join(moves))
            if delivered == self.agent_ids:
                break
        return simualation
