import pygame
from src.models import GraphModel, Hub, Edge, PathStep
from visualizer.renderer import Renderer
from visualizer.map import Map

class Agents(Renderer):
    """
    Class responsible for adding specs on the graph.
    These will reflect turn changes and include:
        - turn number header
        - number of agents (drones) at position per turn.
    Inherits from Map.
    """
    def __init__(self, graph: GraphModel) -> None:
        super().__init__(graph)
        self._map = Map(graph)

    def _turn_counter(self, display_surface: pygame.Surface, turn_header: str) -> None:
        header = self._map.font.render(turn_header, True, "black", None)
        header_rect = header.get_rect(center=(self._screen[0] // 4, self._screen[1] - self._margin))
        pygame.draw.rect(display_surface, "white", header_rect)
        display_surface.blit(header, header_rect)
        return None

    def _turn_blits(self, display_surface: pygame.Surface, turn_state: dict[str, list[str]]) -> None:
        # dynamic path-badge text renderer

        for pos, agent in turn_state.items():
            if '-' in pos and pos not in self.h_positions:
                # found an edge
                hub_names = pos.split('-')
                hub_a, hub_b = hub_names[0], hub_names[1]
                ax, ay = self.h_positions[hub_a]
                bx, by = self.h_positions[hub_b]
                cx, cy = (ax + bx // 2, ay + by // 2)
            else:
                cx, cy = self.h_positions[pos]
            turn_text = self._map.font.render(f"x{len(agent)}", True, "black", None)
            turn_rect = turn_text.get_rect(center=(cx, cy + 20))

            pygame.draw.circle(display_surface, "black", (cx, cy), 10)
            # pygame.draw.rect(display_surface, self.h_color_dict[h], turn_rect)
            display_surface.blit(turn_text, turn_rect)
        return None