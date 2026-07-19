import pygame
from pygame.locals import *

from src.models import GraphModel, Hub, Edge
from visualizer.renderer import Renderer

class Map(Renderer):
    """
    Responsible for rendering the static map.
    """
    def __init__(self, graph: GraphModel) -> None:
        super().__init__(graph)
        self.h_color_dict: dict[str, pygame.Color] = {h.name: pygame.Color(h.color) for h in self.h}

    def _draw_hubs(self, display_surface: pygame.Surface) -> None:
        hub_width: int = 30
        hub_height: int = 20

        for h in self.h:
            cx, cy = self.h_positions[h.name]
            color: pygame.Color = self.h_color_dict[h.name]
            rect = (cx - hub_width // 2, cy - hub_height // 2, hub_width, hub_height)
            pygame.draw.rect(display_surface, color, rect)
        
        return None

    def _draw_edges(self, display_surface: pygame.Surface) -> None:
        for e in self.e:
            p_start: tuple[int, int] = self.h_positions[e.hub_a.name]
            p_end: tuple[int, int] = self.h_positions[e.hub_b.name]
            pygame.draw.line(display_surface, pygame.Color('white'), p_start, p_end, width=3)


if __name__ == "__main__":
    from src.parser import Parser
    filename = "./maps/easy/01_linear_path.txt"
    parser = Parser(filename)

    pygame.init()
    print(pygame.display.get_driver())
    renderer = Map(parser._graph)
    
    display = pygame.display.set_mode(renderer._screen)
    pygame.display.set_caption("FLY-IN")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        display.fill("black")
        renderer._draw_edges(display)
        renderer._draw_hubs(display)
        pygame.display.update()
        clock.tick(60)

    pygame.quit()

