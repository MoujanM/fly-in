import pygame

from src.models import GraphModel, Hub, Edge, PathStep
from visualizer.renderer import Renderer
from visualizer.map import Map


class Blit(Map):
    """
    Class responsible for adding specs on the graph.
    These will reflect turn changes and include:
        - turn number header
        - hub/edge name; max. capacity
        - number of agents (drones) at position per turn.
    Inherits from Renderer.
    """
    def __init__(self, graph: GraphModel,
                 turn_steps: list[PathStep]) -> None:
        super.__init__(graph)
        self.state: dict[str, list[str]] = self._get_turn_state(turn_steps)
        self.agents: list[str] = [s.agent_id for s in turn_steps]
        self._agent_pos: dict[str, str] = {s.agent_id: s.hub_to.name for s in
                                           turn_steps if not s.in_transit}

    def _get_turn_state(self, steps: list[PathStep]) -> dict[str, list[str]]:
        # return dict of {hub.name: list[agent_id]}
        state: dict[str, list[str]] = {}
        occupied_h: list[Hub] = [s.hub_to for s in steps if not s.in_transit]
        for h in occupied_h:
            agents = [s.agent_id for s in steps if s.hub_to.name == h.name]
            state[h.name] = agents
        return state

    def _static_blits(self, display_surface: pygame.Surface) -> None:
        # for hub names, max_cap
        name_font: pygame.Font = pygame.font.SysFont('wasy10', 20)
        info_font: pygame.Font = pygame.font.SysFont('notomono', 10)
        static_txt: list[tuple[pygame.Surface, pygame.Surface]] = []
        for h in self.h:
            name_txt = name_font.render(h.name, True, "black")
            info_txt = info_font.render(f"Max. cap: {h.max_drones}", True, "black")

            static_txt.append((name_txt, info_txt))

