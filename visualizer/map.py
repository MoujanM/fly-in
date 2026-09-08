import pygame
from src.models import GraphModel, Hub, Edge
from visualizer.renderer import Renderer


class Map:
    """
    Responsible for rendering the static map.
    Draws the hubs (with corresponding colors)
    and connections between them (edges).
    """
    def __init__(self, graph: GraphModel) -> None:
        pygame.font.init()
        self.h: list[Hub] = graph.hubs
        self.e: list[Edge] = graph.edges
        self.h_color_dict: dict[str, pygame.Color] = {
            h.name: pygame.Color(h.color) for h in self.h}
        self.font: pygame.font.Font = pygame.font.SysFont('notomono', 11)

    def _draw_hubs(self, display_surface: pygame.Surface,
                   renderer: Renderer) -> None:
        hub_width: int = 60
        hub_height: int = 60

        for h in self.h:
            wcx, wcy = renderer.h_positions[h.name]
            scx, scy = renderer.world_to_camera(wcx, wcy)
            color: pygame.Color = self.h_color_dict[h.name]
            hub_rect = (scx - hub_width // 2,
                        scy - hub_height // 2, hub_width, hub_height)
            pygame.draw.rect(display_surface, color, hub_rect, border_radius=8)

            name_txt = self.font.render(h.name, True, color, None)
            name_rect = name_txt.get_rect(center=(scx, scy - 40))
            pygame.draw.rect(display_surface, "darkslategrey", name_rect)
            display_surface.blit(name_txt, name_rect)

            if h.max_drones is not None:
                info_txt = self.font.render(f"Capacity: {h.max_drones}",
                                            True,
                                            self.h_color_dict[h.name], None)
                info_rect = info_txt.get_rect(center=(scx, scy + 40))
                pygame.draw.rect(display_surface, "darkslategrey", info_rect)
                display_surface.blit(info_txt, info_rect)
        return None

    def _draw_edges(self, display_surface: pygame.Surface,
                    renderer: Renderer) -> None:
        for e in self.e:
            p_start: tuple[int, int] = renderer.h_positions[e.hub_a.name]
            p_end: tuple[int, int] = renderer.h_positions[e.hub_b.name]
            s_start = renderer.world_to_camera(*p_start)
            s_end = renderer.world_to_camera(*p_end)
            pygame.draw.line(display_surface,
                             pygame.Color('white'), s_start, s_end, width=7)
            # if e.max_capacity:
            #     info_txt = self.font.render(f"Capacity: {e.max_capacity}",
            #                                 True, "black", None)
            #     info_rect = info_txt.get_rect(center=(
            #         (s_start[0] + s_end[0]) // 2,
            #         (s_start[1] + s_end[1]) // 2 + 10))
            #     pygame.draw.rect(display_surface, "darkslategrey", info_rect)
            #     display_surface.blit(info_txt, info_rect)
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
