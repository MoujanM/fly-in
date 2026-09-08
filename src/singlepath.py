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
        self.agent_ids: list[str] = []
        for i in range(1, puzzle.nb_agents + 1):
            self.agent_ids.append(f"D{i}")

        self.hubs: list[Hub] = puzzle.hubs
        self.edges: list[Edge] = puzzle.edges
        self.adj_map: dict[str, list[Hub]] = self._build_adj()

    def _build_adj(self) -> dict[str, list[Hub]]:
        adj_map: dict[str, list[Hub]] = {}
        for e in self.edges:
            adj_map.setdefault(e.hub_a.name, []).append(e.hub_b)
            adj_map.setdefault(e.hub_b.name, []).append(e.hub_a)
        return adj_map

    def _heuristic(self, v1: Hub, v2: Hub) -> float:
        # Calculates manhattan distance between two vertices
        # tie-breaker added after updating zone costs
        distance = abs(v1.x - v2.x) + abs(v1.y - v2.y)
        bonus: float = 0
        if v1.zone == 'priority':
            bonus += 0.1
        if v1.zone == 'restricted':
            bonus -= 0.1
        return float(distance) + bonus

    def _move_cost(self, h: Hub) -> int | None:
        z_cost_lookup: dict[str, int] = {
            z.value[0]: z.value[1] for z in ZoneCost}
        return z_cost_lookup[h.zone]

    def _build_path(self, agent_id: str, came_from: dict[tuple[str, int],
                    tuple[Hub, int] | None],
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
            step: PathStep = PathStep(agent_id, prev_s[0], curr_s[0],
                                      prev_s[1], curr_s[1], in_transit)
            path_steps.append(step)
        return path_steps

    def single_agent_path(self, agent_id: str, constraints: list[Constraint]
                          ) -> tuple[list[PathStep], int]:
        """
        Time-expanded A* algorithm.
        Takes agent_id and list of constraints for that agent,
        returns agent's path through graph; start -> goal.

        return value is a tuple:
            - list of hubs traversed with corresponding timestamp,
            - cost of total path movement.
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
        path_steps = self._build_path(agent_id, came_from, goal_state)

        return (path_steps, cost_sum[(goal_state[0].name, goal_state[1])])


if __name__ == "__main__":
    from src.parser import GraphParser
    filename = "./maps/easy/02_simple_fork.txt"
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
