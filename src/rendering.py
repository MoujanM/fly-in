from models import Hub, Edge, GraphModel
from parser import Parser


COLORS = {
    'black': '\033[38;5;0m',
    'red': '\033[38;5;9m',
    'green': '\033[38;5;10m',
    'lime': '\033[38;5;155m',
    'orange': '\033[38;5;202m',
    'yellow': '\033[38;5;11m',
    'blue': '\033[38;5;21m',
    'purple': '\033[38;5;5m',
    'magenta': '\033[38;5;164m',
    'cyan': '\033[38;5;87m',
    'brown': '\033[38;5;100m',
    'gold': '\033[38;5;220m',
    'white': '\033[37m',
    'reset': '\033[0m'
}


def colorize(s: str, color: str) -> str:
    return COLORS[color] + s + COLORS['reset']


class Renderer():
    def __init__(self, graph_model: GraphModel) -> None:
        self.nb_agents: int = graph_model.nb_agents
        self.hubs: list[Hub] = graph_model.hubs
        self.edges: list[Edge] = graph_model.edges
        self.grid: str = self._build_grid()

    def _build_grid(self) -> str:
        hub_lookup: dict[tuple[int, int], Hub] = {(h.x, h.y): h for h in self.hubs}
        max_x: int = max(h.x for h in self.hubs)
        min_x: int = min(h.x for h in self.hubs)
        max_y: int = max(h.y for h in self.hubs)
        min_y: int = min(h.y for h in self.hubs)

        grid_rows: list[str] = []
        for y in range(min_y, max_y + 1):
            row_bits = []
            for x in range(min_x, max_x + 1):
                if (x, y) in hub_lookup:
                    hub = hub_lookup[(x, y)]
                    hub_str = colorize("H", hub.color)
                else:
                    hub_str = colorize("-", 'black')
                row_bits.append(hub_str)
            grid_rows.append(" ".join(row_bits))

        return '\n'.join(grid_rows)


if __name__ == "__main__":
    filename = "./maps/easy/02_simple_fork.txt"
    parser = Parser(filename)
    # print(parser._hubs)
    renderer = Renderer(parser._graph)

    print(renderer.grid)

        