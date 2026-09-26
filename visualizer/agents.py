import pygame
from src.models import GraphModel
from visualizer.renderer import Renderer
from visualizer.map import Map


class Agents:
    """Render dynamic agent counts and simulation status.

    Args:
        graph: Validated graph used to create the static map renderer.
    """

    def __init__(self, graph: GraphModel) -> None:
        """Create the static map resources used by dynamic rendering.

        Args:
            graph: Validated graph used for hub styling and fonts.

        Returns:
            None.
        """
        self._map = Map(graph)

    def _turn_counter(self, display_surface: pygame.Surface,
                      renderer: Renderer, turn_header: str) -> None:
        """Draw the current turn header at the bottom of the display.

        Args:
            display_surface: Surface on which the header should be drawn.
            renderer: Renderer providing display dimensions and margins.
            turn_header: Text describing the current simulation turn.

        Returns:
            None.
        """
        header = self._map.font.render(turn_header, True, "darkblue", None)
        header_rect = header.get_rect(
            center=(renderer.display_size[0] // 2,
                    renderer.display_size[1] - renderer._margin))
        pygame.draw.rect(display_surface, "cornsilk3", header_rect)
        display_surface.blit(header, header_rect)
        return None

    def _turn_blits(self, display_surface: pygame.Surface,
                    renderer: Renderer, turn_state: dict[str, list[str]]
                    ) -> None:
        """Draw an agent-count badge at each occupied position.

        Args:
            display_surface: Surface on which badges should be drawn.
            renderer: Renderer providing hub positions and camera transforms.
            turn_state: Mapping from positions to agents at those positions.

        Returns:
            None.
        """
        for pos, agent in turn_state.items():
            if pos in renderer.h_positions:
                cx, cy = renderer.h_positions[pos]
                scx, scy = renderer.world_to_camera(cx, cy)
            else:
                # found an edge
                hub_names = pos.split('-')
                hub_a, hub_b = hub_names[0], hub_names[1]
                ax, ay = renderer.h_positions[hub_a]
                bx, by = renderer.h_positions[hub_b]
                cx, cy = ((ax + bx) // 2, (ay + by) // 2)
                scx, scy = renderer.world_to_camera(cx, cy)

            turn_text = self._map.font.render(f"x{len(agent)}", True,
                                              "black", None)
            turn_rect = turn_text.get_rect(center=(scx, scy + 20))

            pygame.draw.circle(display_surface, "black", (scx, scy), 10)
            display_surface.blit(turn_text, turn_rect)
        return None
