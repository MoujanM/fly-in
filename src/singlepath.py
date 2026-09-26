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
        """Estimate the remaining movement cost between two hubs.

        Args:
            v1: Current hub.
            v2: Goal hub.

        Returns:
            Manhattan distance with a small zone-based tie-breaker.
        """
        distance = abs(v1.x - v2.x) + abs(v1.y - v2.y)
        bonus: float = 0
        if v1.zone == 'priority':
            bonus += 0.1
        if v1.zone == 'restricted':
            bonus -= 0.1
        return float(distance) + bonus

    def _move_cost(self, h: Hub) -> int | None:
        """Return the movement cost associated with a hub's zone.
        Args:
            h: Hub being entered.
        Returns:
            The number of turns required, or ``None`` for blocked zones.
        """
        z_cost_lookup: dict[str, int] = {
            z.value[0]: z.value[1] for z in ZoneCost}
        return z_cost_lookup[h.zone]

    def _build_path(self, agent_id: str, came_from: dict[tuple[str, int],
                    tuple[Hub, int] | None],
                    goal_state: tuple[Hub, int]) -> list[PathStep]:
        """Reconstruct timestamped path steps from A* predecessor links.
        Args:
            agent_id: Identifier of the agent whose path was searched.
            came_from: Predecessor mapping keyed by hub name and time.
            goal_state: Goal hub and arrival time.
        Returns:
            Ordered path steps from the start hub to the goal.
        """

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
            step: PathStep = PathStep(agent_id, prev_s[0], curr_s[0],
                                      prev_s[1], curr_s[1], in_transit)
            path_steps.append(step)
        return path_steps

    def single_agent_path(self, agent_id: str, constraints: list[Constraint]
                          ) -> tuple[list[PathStep], int]:
        """Find a minimum-cost path with time and position constraints.
        Args:
            agent_id: Identifier of the agent to route.
            constraints: Hub or connection reservations to avoid.
        Returns:
            A tuple containing timestamped path steps and total path cost.
        """
        forbidden: set[tuple[str, int]] = {
            (c.position, c.t) for c in constraints if c.agent_id == agent_id}
        # think of v as state of <hub, timestamp>
        v_start: tuple[Hub, int] = (next(
            h for h in self.hubs if h.kind == 'start_hub'), 0)
        v_goal: Hub = next(h for h in self.hubs if h.kind == 'end_hub')

        came_from: dict[tuple[str, int], tuple[Hub, int] | None] = {
            (v_start[0].name, v_start[1]): None}
        cost_sum: dict[tuple[str, int], int] = {
            (v_start[0].name, v_start[1]): 0}

        counter = itertools.count()     # tie-breaker
        hq: list[tuple[float, int, tuple[Hub, int]]] = [
            (0.0, next(counter), v_start)]  # (priority, tiebreaker, state)

        while hq:
            priority, _, current_state = heapq.heappop(hq)
            if current_state[0].name == v_goal.name:
                goal_state = current_state
                break
            curr_hub, t = current_state
            neighbours = self.adj_map.get(curr_hub.name, [])
            move_opts: list[Hub] = neighbours + [curr_hub]
            for h in move_opts:
                if h == curr_hub:
                    # wait action costs 1
                    turns: int | None = 1
                else:
                    turns = self._move_cost(h)
                if turns is None:
                    continue
                new_state_key = (h.name, t + turns)
                if new_state_key in forbidden:
                    continue
                if h != curr_hub:
                    edge_name = f"{curr_hub.name}-{h.name}"
                    if (edge_name, t) in forbidden:
                        continue
                    # if turns == 2 and (edge_name, t) in forbidden:
                    #     continue
                new_cost = cost_sum[(curr_hub.name, t)] + turns
                if (new_state_key not in cost_sum or
                        new_cost < cost_sum[new_state_key]):
                    cost_sum[(new_state_key)] = new_cost
                    priority = new_cost + self._heuristic(h, v_goal)
                    heapq.heappush(hq, (priority, next(counter),
                                        (h, t + turns)))
                    came_from[new_state_key] = current_state
        if 'goal_state' not in locals():
            print(f"A* failed for {agent_id}. "
                  f"Constraints: {[c for c in constraints if c.agent_id == agent_id]}")
            return [], 0
        path_steps = self._build_path(agent_id, came_from, goal_state)

        return (path_steps, cost_sum[(goal_state[0].name, goal_state[1])])


if __name__ == "__main__":
    from src.parser import GraphParser
    filename = "maps/easy/01_linear_path.txt"
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
