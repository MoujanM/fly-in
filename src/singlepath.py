from src.models import GraphModel, Hub, Edge, ZoneCost, PathStep, Constraint
import heapq
import itertools


class PathFinder():
    """
    Class takes GraphModel, includes implementation of A*;
    for single-agent path-finding.
    Parent class to CBS - multi-agent, conflict-detecting
    path-finding algorithm.

    On initialization, class creates attributes to hold graph specs:
        - list of unique agent (drone) IDs
        - list of all hubs and edges (connections)
        - graph's adjacency map (to be used by class methods)
        - a look-up dict for hub zones and corresponding costs.
    """

    def __init__(self, puzzle: GraphModel) -> None:
        """Initialize graph structures used by single-agent A* search.

        Args:
            puzzle: Validated graph to search.

        Returns:
            None.
        """
        self.agent_ids: list[str] = []
        for i in range(1, puzzle.nb_agents + 1):
            self.agent_ids.append(f"D{i}")

        self.hubs: list[Hub] = puzzle.hubs
        self.edges: list[Edge] = puzzle.edges
        self.adj_map: dict[str, list[Hub]] = self._build_adj()

    def _build_adj(self) -> dict[str, list[Hub]]:
        """Build an adjacency list from the graph's bidirectional edges.

        Returns:
            A mapping from hub name to neighboring hubs.
        """
        adj_map: dict[str, list[Hub]] = {}
        for e in self.edges:
            adj_map.setdefault(e.hub_a.name, []).append(e.hub_b)
            adj_map.setdefault(e.hub_b.name, []).append(e.hub_a)
        return adj_map

    def _heuristic(self, v1: Hub, v2: Hub) -> float:
        """
        Admissible and consistent Manhattan distance heuristic.
        Tiny tie-breaker is strictly smaller than minimum edge cost.
        """
        dx = abs(v1.x - v2.x)
        dy = abs(v1.y - v2.y)
        distance = dx + dy
        tie_breaker = 0.0001 * distance
        return float(distance + tie_breaker)

    def _move_cost(self, h: Hub) -> int | None:
        z_cost_lookup: dict[str, int] = {
            z.value[0]: z.value[1] for z in ZoneCost}
        return z_cost_lookup.get(h.zone)

    def _build_path(self, agent_id: str,
                    came_from: dict[tuple[str, int], tuple[Hub, int] | None],
                    goal_state: tuple[Hub, int]) -> list[PathStep]:
        path: list[tuple[Hub, int]] = []
        crumbs: tuple[Hub, int] | None = goal_state
        while crumbs is not None:
            path.append(crumbs)
            crumbs = came_from.get((crumbs[0].name, crumbs[1]))
        path.reverse()

        path_steps: list[PathStep] = []
        for prev_s, curr_s in zip(path, path[1:]):
            turns_taken = curr_s[1] - prev_s[1]
            is_moving = curr_s[0].name != prev_s[0].name
            in_transit = is_moving and turns_taken == 2
            step = PathStep(agent_id, prev_s[0], curr_s[0],
                            prev_s[1], curr_s[1], in_transit)
            path_steps.append(step)
        return path_steps

    def single_agent_path(self, agent_id: str,
                          constraints: list[Constraint]
                          ) -> tuple[list[PathStep], float]:
        """
        Time-expanded A* with upper bound time horizon.
        Returns empty path with infinite cost if goal unreachable
        under the given constraints.
        """
        forbidden: set[tuple[str, int]] = {
            (c.position, c.t) for c in constraints if c.agent_id == agent_id
        }

        v_start_hub = next(h for h in self.hubs if h.kind == 'start_hub')
        v_goal_hub = next(h for h in self.hubs if h.kind == 'end_hub')
        v_start: tuple[Hub, int] = (v_start_hub, 0)

        # time-horizon bound (t_max) prevents looping when agent blocked
        max_constraint_t = max(
            (c.t for c in constraints if c.agent_id == agent_id),
            default=0
        )
        t_max = (len(self.hubs) * 2) + max_constraint_t + 30
        # print(f"A*'s t_max: {t_max}")
        came_from: dict[tuple[str, int], tuple[Hub, int] | None] = {
            (v_start[0].name, v_start[1]): None
        }
        cost_sum: dict[tuple[str, int], float] = {
            (v_start[0].name, v_start[1]): 0.0
        }

        counter = itertools.count()
        hq: list[tuple[float, int, tuple[Hub, int]]] = [
            (self._heuristic(v_start[0], v_goal_hub), next(counter), v_start)
        ]
        goal_state: tuple[Hub, int] | None = None

        while hq:
            priority, _, current_state = heapq.heappop(hq)
            curr_hub, t = current_state

            if curr_hub.name == v_goal_hub.name:
                goal_state = current_state
                break

            if t >= t_max:
                continue

            neighbours = self.adj_map.get(curr_hub.name, [])
            move_opts: list[Hub] = neighbours + [curr_hub]

            for h in move_opts:
                turns = 1 if h == curr_hub else self._move_cost(h)
                if turns is None:
                    continue

                new_t = t + turns
                if new_t > t_max:
                    continue

                new_state_key = (h.name, new_t)
                if new_state_key in forbidden:
                    continue

                if h != curr_hub and turns == 2:
                    edge_name = Edge.canonical_name(h.name, curr_hub.name)
                    if any((edge_name, check_t) in forbidden
                           for check_t in range(t, new_t)):
                        continue
                # prefer priority zones, distinct from heuristic
                actual_turns = turns
                if h.zone == 'priority' and h != curr_hub:
                    priority_discount = 0.001
                    new_cost = cost_sum[
                        (curr_hub.name, t)] + actual_turns - priority_discount
                else:
                    new_cost = cost_sum[(curr_hub.name, t)] + actual_turns

                if (new_state_key not in cost_sum or
                        new_cost < cost_sum[new_state_key]):
                    cost_sum[new_state_key] = new_cost
                    f = new_cost + self._heuristic(h, v_goal_hub)
                    came_from[new_state_key] = current_state
                    heapq.heappush(hq, (f, next(counter), (h, new_t)))

        if goal_state is None:
            return ([], float('inf'))

        path_steps = self._build_path(agent_id, came_from, goal_state)
        return (path_steps, cost_sum[(goal_state[0].name, goal_state[1])])


if __name__ == "__main__":
    from src.parser import GraphParser
    filename = "maps/medium/02_circular_loop.txt"
    parser = GraphParser(filename)
    solver = PathFinder(parser._graph)
    # print(solver.agent_ids)
    for agent in solver.agent_ids:
        print(f"{agent} ==> {solver.single_agent_path(agent, [])}")
    # print(parser._hubs)
    # solver = SingleAgent(parser._graph)
    # path, cost = solver.a_star_finder()
    # print(f"Path to walk: {path}")
    # print(f"Cost of path walked: {cost}")
    # print(f"Total cost: {cost[-1][-1]}")
