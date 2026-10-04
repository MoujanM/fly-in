from src.models import GraphModel, PathStep, CBSResult


class SimController:
    """Manage simulation state for the visualizer.

    Args:
        graph: Validated graph containing the simulation's hubs.
        result: Conflict-free plan produced by the CBS solver.
    """

    def __init__(self, graph: GraphModel, result: CBSResult):
        """Build turn-indexed state from a solved joint plan.

        Args:
            graph: Validated graph containing the simulation's hubs.
            result: Conflict-free plan produced by the CBS solver.

        Returns:
            None.
        """
        self.result: CBSResult = result
        self.agents: list[str] = list(result.joint_plan.keys())
        self.turn_map: dict[int, list[PathStep]] = self._get_turn_map()
        self.output: dict[int, list[str]] = self._get_sim_desc()

        self.current_turn: int = 0
        self.max_turn: int = max(self.turn_map.keys()) + 1
        self.delivered: set[str] = set()
        self._agent_positions: dict[str, str] = {}
        self.goal: str = next(
            h.name for h in graph.hubs if h.kind == "end_hub")

        start_name = next(h.name for h in graph.hubs if h.kind == "start_hub")
        for agent in self.agents:
            self._agent_positions[agent] = start_name

    def _get_turn_map(self) -> dict[int, list[PathStep]]:
        """Expand each plan into the steps visible at every turn.

        Returns:
            A mapping from turn number to the path steps active then.
        """
        turn_map: dict[int, list[PathStep]] = {}
        for agent, path in self.result.joint_plan.items():
            for step in path:
                turn_map.setdefault(step.t_depart, []).append(step)
                if step.in_transit:
                    for mid_t in range(step.t_depart + 1, step.t_arrive):
                        present = PathStep(
                            agent_id=agent,
                            hub_from=step.hub_from,
                            hub_to=step.hub_to,
                            t_depart=mid_t,
                            t_arrive=step.t_arrive,
                            in_transit=True
                        )
                        turn_map.setdefault(mid_t, []).append(present)
                    arrival = PathStep(
                        agent_id=agent,
                        hub_from=step.hub_to,
                        hub_to=step.hub_to,
                        t_depart=step.t_arrive,
                        t_arrive=step.t_arrive,
                        in_transit=False
                    )
                    turn_map.setdefault(step.t_arrive, []).append(arrival)
        return turn_map

    def get_turn_state(self) -> dict[str, list[str]]:
        """Return undelivered agents grouped by their current position.

        Returns:
            A mapping from hub or connection name to agent identifiers.
        """
        state: dict[str, list[str]] = {}
        for agent, pos in self._agent_positions.items():
            # if agent not in self.delivered:
            state.setdefault(pos, []).append(agent)
        return state

    # def final_state(self) -> dict[str, list[str]]:
    #     """Return all agents grouped by their final recorded position.

    #     Returns:
    #         A mapping from position name to agent identifiers.
    #     """
    #     state: dict[str, list[str]] = {}
    #     for agent, position in self._agent_positions.items():
    #         state.setdefault(position, []).append(agent)
    #     return state

    def _get_sim_desc(self) -> dict[int, list[str]]:
        """Create printable movement descriptions for each active turn.

        Returns:
            One human-readable movement description per simulation turn.
        """
        turn_map: dict[int, list[PathStep]] = {}
        for agent, path in self.result.joint_plan.items():
            for step in path:
                turn_map.setdefault(step.t_depart, []).append(step)

        delivered: set[str] = set()
        simulation: dict[int, list[str]] = {}
        for turn in sorted(turn_map.keys()):
            moves = []
            for step in turn_map[turn]:
                if step.agent_id in delivered:
                    continue
                if step.hub_from == step.hub_to:
                    continue
                if step.in_transit:
                    edge: str = f"{step.hub_from.name}-{step.hub_to.name}"
                    moves.append(f"{step.agent_id}-{edge}")
                else:
                    moves.append(f"{step.agent_id}-{step.hub_to.name}")
                if step.hub_to.kind == "end_hub" and not step.in_transit:
                    delivered.add(step.agent_id)
            simulation.setdefault(turn, []).append(" ".join(moves))
            if delivered == set(self.agents):
                break
        return simulation

    def get_turn_steps(self) -> list[PathStep]:
        """Return the path steps scheduled for the current turn."""
        return self.turn_map[self.current_turn]

    def advance_turn(self) -> None:
        """Advance the simulation to its next scheduled turn.

        Delivered agents are removed from the active view, and agents still
        travelling are represented by their connection name.
        """
        remaining_turns: list[int] = [
            t for t in self.turn_map if t > self.current_turn]
        if not remaining_turns:
            for agent in self.agents:
                self._agent_positions[agent] = self.goal
            self.current_turn = self.max_turn
            # self.delivered = set(self.agents)
            return
        next_turn = min(remaining_turns)
        steps = self.get_turn_steps()

        for step in steps:
            if step.in_transit:
                edge_name = f"{step.hub_from.name}-{step.hub_to.name}"
                prev_pos: str = self._agent_positions[step.agent_id]
                if '-' in prev_pos:
                    # previously on connection
                    if step.t_depart == self.current_turn:
                        self._agent_positions[step.agent_id] = step.hub_to.name
                else:
                    self._agent_positions[step.agent_id] = edge_name
                continue
            else:
                self._agent_positions[step.agent_id] = step.hub_to.name
            if step.hub_to.kind == "end_hub":
                self.delivered.add(step.agent_id)
        self.current_turn = next_turn
        return None

    def turn_header(self) -> str:
        """Format the current turn and agent count for the visualizer.

        Returns:
            A display-ready simulation status string.
        """
        return (f"Turn {self.current_turn} / {self.max_turn}"
                f" (nb_agents: {len(self.agents)})")
