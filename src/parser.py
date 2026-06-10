from structs import Hub, Edge
import re

# constant mod variables for efficient parsing
HUB_PATTERN: re.Pattern = re.compile(r'(?P<kind>\w+_hub|hub):\s+',
)


class Parser():
    """
    start_hub will be start_point - x, y
    hubs will be zones (to move through), with costs & capacity - x, y
    end_hub will be goal - x, y

    connection always between two zones; with capacity
    """
    def __init__(self) -> None:
        self._graph_specs: dict[str, str] = {"agents": 0, "hubs": [], "edges": []}

    def read_to_dict(self, path_to_file: str) -> dict[str, str]:
        """function to read and return the following:
        drone_count;
        all hubs (vertices) marking start/end;
        all connections (edges)
        """
        
        with open(path_to_file) as f:
            for line in f:
                if not (line.startswith("#") or line.isspace()):
                    key, value = line.split(":", 1)
                    if "drone" in key:
                        self._graph_specs["agents"] = value.strip()
                    elif "hub" in key:
                        self._graph_specs["hubs"].append(value.strip())
                    elif "connect" in key:
                        self._graph_specs["edges"].append(value.strip())        
        return self._graph_specs


    def get_game_stat(self) -> dict:
        for hub in graph_specs["hubs"]:
            name, x, y, meta_data = hub.split(' ', 3)
            hub = Hub(name, x, y)
            
            # add metadata parsing
            # meta_data_count = len(meta_data.split(' '))
        for edge in graph_specs["edges"]:
            edge = Edge(*edge.split('-'))

        return graph_specs
        



if __name__ == "__main__":
    filename = "maps/easy/01_linear_path.txt"
    parser = Parser()
    specs = parser.read_to_dict(filename)
    graph = parser.get_game_stat(specs)
    print(graph)
        