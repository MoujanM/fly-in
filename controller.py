import pygame
from src.models import GraphModel, Hub, Edge, PathStep, CBSResult
from visualizer.renderer import Renderer
from visualizer.map import Map

class SimController():
    """
    Class responsible for managing sim states.
    Gets states from src/ and hands to visualizer.
    """
    def __init__(self, graph: GraphModel, result: CBSResult):
        self.agents: list[str] = list(result.joint_plan.keys())
        self.turn_map: dict[int, list[PathStep]] = self._get_turn_map(result)
        self.output: list[str] = self._get_sim_desc()

        self.current_turn: int = 0
        self.max_turn: int = max(self.turn_map.keys()) + 1
        self.delivered: set[str] = set()
        self._agent_positions: dict[str, str] = {}

        start_name = next(h.name for h in graph.hubs if h.kind == "start_hub")
        for agent in self.agents:
            self._agent_positions[agent] = start_name

    def _get_turn_map(self, result: CBSResult) -> dict[int, list[PathStep]]:
        # return dict of {turn_nb: list[steps]}
        turn_map: dict[int, list[PathStep]] = {}

        for agent, path in result.joint_plan.items():
            for step in path:
                turn_map.setdefault(step.t_depart, []).append(step)
        return turn_map

    def get_turn_state(self) -> dict[str, list[str]]:
        # return dict of {hub.name: list[agent_id]} for current turn
        state: dict[str, list[str]] = {}
        for agent, hub in self._agent_positions.items():
            if agent not in self.delivered:
                state.setdefault(hub, []).append(agent)
        return state

    def final_state(self) -> dict[str, list[str]]:
        # no delivered filter
        state: dict[str, list[str]] = {}
        for agent, position in self._agent_positions.items():
            state.setdefault(position, []).append(agent)
        return state

    def _get_sim_desc(self) -> list[str]:
        delivered: set[str] = set()
        simualation: list[str] = []
        
        for turn in sorted(self.turn_map.keys()):
            moves = []
            for step in self.turn_map[turn]:
                if step.agent_id in delivered:
                    continue
                if step.hub_from == step.hub_to:
                    continue
                if step.in_transit:
                    connection: str = f"{step.hub_from.name}-{step.hub_to.name}"
                    moves.append(f"{step.agent_id}-{connection}")
                else:
                    moves.append(f"{step.agent_id}-{step.hub_to.name}")
                if step.hub_to.kind == "end_hub" and not step.in_transit:
                    delivered.add(step.agent_id)
            if moves:
                simualation.append(" ".join(moves))
            if delivered == set(self.agents):
                break
        return simualation

    def get_turn_steps(self) -> list[PathStep]:
        return self.turn_map[self.current_turn]

    def advance_turn(self) -> None:
        remaining_turns: list[int] = [t for t in self.turn_map if t > self.current_turn]
        if not remaining_turns:
            for agent in self.agents:
                self._agent_positions[agent] = "goal"
            self.jump_to_end()
            return
        next_turn = min(remaining_turns)
        steps = self.get_turn_steps()
        for step in steps:
            if step.in_transit:
                edge_name = f"{step.hub_from.name}-{step.hub_to.name}"
                self._agent_positions[step.agent_id] = edge_name
            else:
                self._agent_positions[step.agent_id] = step.hub_to.name
            if step.hub_to.kind == "end_hub":
                self.delivered.add(step.agent_id)
        self.current_turn = next_turn
        return None

    def jump_to_end(self) -> None:
        self.current_turn = self.max_turn
        self.delivered = set(self.agents)
        return None

    def turn_header(self) -> str:
        return f"Turn {self.current_turn} / {self.max_turn} (nb_agents: {len(self.agents)})"
    
    def sim_complete(self) -> bool:
        return self.delivered == set(self.agents)