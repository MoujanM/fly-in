from src.models import GraphModel, Hub, Edge


class Renderer:
    """
    Parent Renderer - takes graph and computes & stores the following:
        - size of Display Surface
        - pixel scalar and grid offset values
        - pixel coordinates of hubs
    These are passed to child classes for easy & fast drawing.
    """
    def __init__(self, graph: GraphModel) -> None:
        self.h: list[Hub] = graph.hubs
        self.e: list[Edge] = graph.edges

        self.display_size: tuple[int, int] = (1500, 800)
        self._scale: int = 140
        self._margin: int = 40
        self.h_positions: dict[str, tuple[int, int]] = self._get_h_positions()
        self.camera_x, self.camera_y = self._init_camera()
        self.zoom: float = 1.0

    def _logical_to_world(self, x: int, y: int) -> tuple[int, int]:
        return (x * self._scale, y * self._scale)

    def world_to_camera(self, wx: int, wy: int) -> tuple[float, float]:
        return ((wx * self.zoom + self.camera_x),
                (wy * self.zoom + self.camera_y))

    def _init_camera(self) -> tuple[float, float]:
        """
        Function to compute where in the screen to put drawings.
        """
        min_x: int = min(h.x for h in self.h)
        max_x: int = max(h.x for h in self.h)
        min_y: int = min(h.y for h in self.h)
        max_y: int = max(h.y for h in self.h)

        world_centre: tuple[float, float] = ((min_x + max_x) / 2 * self._scale,
                                             (min_y + max_y) / 2 * self._scale)
        screen_w, screen_h = self.display_size

        camera_x: float = screen_w / 2 - world_centre[0]
        camera_y: float = screen_h / 2 - world_centre[1]

        return (camera_x, camera_y)

    def zoom_point(self, z_factor: float) -> None:
        screen_w, screen_h = self.display_size
        pivot: tuple[int, int] = (screen_w // 2, screen_h // 2)
        px, py = pivot
        z_old = self.zoom
        z_new = max(0.1, min(5.0, z_old * z_factor))
        factor: float = z_new / z_old

        self.camera_x = px - (px - self.camera_x) * factor
        self.camera_y = py - (py - self.camera_y) * factor
        self.zoom = z_new
        return None

    def _get_h_positions(self) -> dict[str, tuple[int, int]]:
        positions: dict[str, tuple[int, int]] = {}
        for h in self.h:
            pixels = self._logical_to_world(h.x, h.y)
            positions.update({h.name: (pixels[0], pixels[1])})
        return positions
