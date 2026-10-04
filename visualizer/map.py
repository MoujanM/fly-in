import pygame
from src.models import GraphModel, Hub, Edge
from visualizer.renderer import Renderer


class Map:
    """Render the static hubs and connections of a graph.

    Args:
        graph: Validated graph to render.
    """

    def __init__(self, graph: GraphModel) -> None:
        """Prepare graph geometry, colors, and the label font.

        Args:
            graph: Validated graph to render.

        Returns:
            None.
        """
        pygame.font.init()
        self.h: list[Hub] = graph.hubs
        self.e: list[Edge] = graph.edges
        self.h_color_dict: dict[str, pygame.Color] = {
            h.name: self._get_safe_color(h.color) for h in self.h}
        self.font: pygame.font.Font = pygame.font.SysFont('notomono', 11)

    def _get_safe_color(self, color: str) -> pygame.Color:
        try:
            return pygame.Color(color)
        except ValueError:
            return pygame.Color("white")

    def _draw_hubs(self, display_surface: pygame.Surface,
                   renderer: Renderer) -> None:
        """Draw each hub, its name, and its drone capacity.

        Args:
            display_surface: Surface on which hubs should be drawn.
            renderer: Coordinate transformer for the current camera view.

        Returns:
            None.
        """
        hub_width: int = 60
        hub_height: int = 60

        for h in self.h:
            wcx, wcy = renderer.h_positions[h.name]
            scx, scy = renderer.world_to_camera(wcx, wcy)
            color: pygame.Color = self.h_color_dict[h.name]
            hub_rect = (scx - hub_width // 2,
                        scy - hub_height // 2, hub_width, hub_height)
            pygame.draw.rect(display_surface, color, hub_rect, border_radius=8)

            name_txt = self.font.render(h.name, True, "darkblue", None)
            name_rect = name_txt.get_rect(center=(scx, scy - 40))
            pygame.draw.rect(display_surface, "cornsilk3", name_rect)
            display_surface.blit(name_txt, name_rect)

            if h.max_drones is not None:
                info_txt = self.font.render(f"zn={h.zone};cp={h.max_drones}",
                                            True,
                                            "darkblue", None)
                info_rect = info_txt.get_rect(center=(scx, scy + 40))
                pygame.draw.rect(display_surface, "cornsilk3", info_rect)
                display_surface.blit(info_txt, info_rect)
        return None

    def _draw_edges(self, display_surface: pygame.Surface,
                    renderer: Renderer) -> None:
        """Draw every graph connection as a line.

        Args:
            display_surface: Surface on which edges should be drawn.
            renderer: Coordinate transformer for the current camera view.

        Returns:
            None.
        """
        for e in self.e:
            p_start: tuple[int, int] = renderer.h_positions[e.hub_a.name]
            p_end: tuple[int, int] = renderer.h_positions[e.hub_b.name]
            s_start = renderer.world_to_camera(*p_start)
            s_end = renderer.world_to_camera(*p_end)
            pygame.draw.line(display_surface,
                             pygame.Color('white'), s_start, s_end, width=7)
            if e.max_capacity > 1:
                info_txt = self.font.render(f"cp: {e.max_capacity}",
                                            True, "darkblue", None)
                info_rect = info_txt.get_rect(center=(
                    (s_start[0] + s_end[0]) // 2,
                    (s_start[1] + s_end[1]) // 2 + 10))
                pygame.draw.rect(display_surface, "cornsilk3", info_rect)
                display_surface.blit(info_txt, info_rect)
        return None

# if __name__ == "__main__":
#     from src.parser import GraphParser
#     filename = "./maps/easy/01_linear_path.txt"
#     parser = GraphParser(filename)

#     pygame.init()
#     # print(pygame.display.get_driver())
#     renderer = Map(parser._graph)

#     display = pygame.display.set_mode(renderer._screen)
#     pygame.display.set_caption("FLY-IN")
#     clock = pygame.time.Clock()

#     running = True
#     while running:
#         for event in pygame.event.get():
#             if event.type == pygame.QUIT:
#                 running = False
#         display.fill("grey")
#         renderer._draw_edges(display)
#         renderer._draw_hubs(display)
#         pygame.display.update()
#         clock.tick(60)

#     pygame.quit()
#     pygame.font.init()
#     fonts = pygame.font.get_fonts()
#     for font in fonts:
#         print(font)
#     pygame.quit()
