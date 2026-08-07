import pygame
from src.models import GraphModel, Hub, Edge


class Renderer():
    """
    Parent Renderer - takes graph and computes & stores the following:
        - size of Display Surface
        - pixel scalar and grid offset values
        - pixel coordinates of hubs
    These are passed to child classes for easy & fast drawing.
    """
    def __init__(self, graph: GraphModel) -> None:
        self._scale: int = 150
        self._margin: int = 100

        self.h: list[Hub] = graph.hubs
        self.e: list[Edge] = graph.edges
        
        self._screen: tuple[int, int] = self._ds_size()
        self._offset: tuple[int, int] = self._compute_offset()
        self.h_positions: dict[str, tuple[int, int]] = self._get_h_positions()
    
    def _ds_size(self) -> tuple[int, int]:
        """Function to determine size of display surface.
        min_size is defined, else using graph to determine width & height.
        """
        # individually defined to play with later
        min_size: int = 400
        span_x: int = max(h.x for h in self.h) - min(h.x for h in self.h)
        span_y: int = max(h.y for h in self.h) - min(h.y for h in self.h)

        ds_w: int = max(span_x * self._scale + 2 * self._margin, min_size)
        ds_h: int = max(span_y * self._scale + 2 * self._margin, min_size)

        return ds_w, ds_h

    def _compute_offset(self) -> tuple[int, int]:
        """
        Function to compute where in the screen to put drawings.
        """
        min_x: int = min(h.x for h in self.h)
        max_x: int = max(h.x for h in self.h)
        min_y: int = min(h.y for h in self.h)
        max_y: int = max(h.y for h in self.h)

        screen_w: int = self._screen[0] - 2 * self._margin
        screen_h: int = self._screen[1] - 2 * self._margin

        span_x: int = max_x - min_x
        span_y: int = max_y - min_y

        offset_x: int = self._margin + (-min_x * self._scale)
        offset_y: int = screen_h // 2 + self._margin + (-min_y * self._scale)
        
        return (offset_x, offset_y)
    
    def _pixel_scaler(self, x: int, y: int) -> tuple[int, int]:
        """Takes logical coordinates, returns physical ones."""
        return (x * self._scale + self._offset[0], y * self._scale + self._offset[1])

    def _get_h_positions(self) -> dict[str, tuple[int, int]]:
        positions: dict[str, tuple[int, int]] = {}
        for h in self.h:
            pixels = self._pixel_scaler(h.x, h.y)
            positions.update({h.name: (pixels[0], pixels[1])})
        return positions
