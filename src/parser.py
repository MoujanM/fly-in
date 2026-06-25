from models import Hub, Edge, GraphModel
import re

# constant mod variables for efficient parsing
# naming captured groups using (?P<name>pattern)
HUB_PATTERN: re.Pattern = re.compile(r'(?P<kind>\w+_hub|hub):\s+'
                                     r'(?P<name>\w+)\s+'
                                     r'(?P<x>-?\d+)\s+(?P<y>-?\d+)'
                                     r'(?:\s+\[(?P<meta>[^\]]*)\])?')
EDGE_PATTERN: re.Pattern = re.compile(
    r'connection:\s+(?P<hub_a>\w+)-(?P<hub_b>\w+)'
    r'(?:\s+\[(?P<meta>[^\]]*)\])?')

META_KV_PATTERN: re.Pattern = re.compile(r'(\w+)=(\w+)')


class Parser():
    """
    Parser class with functions to parse the input file,
    and the lines within it and build a workable game stat.
    Builds all hubs and edges of the graph.
    """
    def __init__(self, filename: str) -> None:
        self.filename: str = filename
        self._hubs: list[Hub] = []
        self._edges: list[Edge] = []
        self._graph: GraphModel = self.get_graph()

    def parse_meta(self, metadata: str) -> dict[str, str]:
        metadata_list: list = META_KV_PATTERN.findall(metadata)
        if not metadata_list:
            raise Exception("Error parsing metadata - check input file.")
        return dict(metadata_list)

    def parse_return_hub(self, hub_str: str) -> Hub:
        """
        Function that takes a string. tries to match with hub_pattern.
        if there is a match, returns Hub object.
        """
        m: re.Match = HUB_PATTERN.match(hub_str)
        if not m:
            raise Exception("Error parsing hub line - check input file.")
        metadata: dict[str, str] = {}
        if m.group('meta'):
            metadata = self.parse_meta(m.group('meta'))

        try:
            new_hub = Hub(
                kind=m.group('kind'),
                name=m.group('name'),
                x=int(m.group('x')),
                y=int(m.group('y')),
                zone=metadata.get('zone'),
                color=metadata.get('color'),
                max_drones=int(metadata.get('max_drones', 1)))
            return new_hub
        except Exception as e:
            raise e

    def parse_return_edge(self, edge_str) -> Edge:
        m: re.Match = EDGE_PATTERN.match(edge_str)
        if not m:
            raise Exception("Error parsing connection - check input file.")

        hub_name_lookup: dict[str, Hub] = {h.name: h for h in self._hubs}
        
        try:
            hub_a: Hub = hub_name_lookup[m.group('hub_a')]
            hub_b: Hub = hub_name_lookup[m.group('hub_b')]

            metadata: dict[str, str] = {}
            if m.group('meta'):
                metadata = self.parse_meta(m.group('meta'))

            new_edge = Edge(
                hub_a=hub_a,
                hub_b=hub_b,
                max_capacity=int(metadata.get('max_link_capacity', 1))
                )
            return new_edge
        except Exception as e:
            raise e

    def _read_to_dict(self) -> dict[str, int | list[Hub | Edge]]:
        """function to read and return the following:
        drone_count;
        all hubs (vertices) marking start/end;
        all connections (edges)
        """
        nb_agents: int = None
        graph_dict: dict[str, int | list[Hub | Edge]] = {}
        with open(self.filename) as f:
            for line in f:
                if line.startswith("#") or line.isspace():
                    continue
                if line.startswith('nb_drones'):
                    nb_agents = int(line.split(':')[1].strip())
                elif 'hub' in line:
                    if self.parse_return_hub(line):
                        self._hubs.append(self.parse_return_hub(line))
                elif 'connection' in line:
                    if self.parse_return_edge(line):
                        self._edges.append(self.parse_return_edge(line))

        graph_dict.update({'nb_agents': nb_agents,
                           'hubs': self._hubs,
                           'edges': self._edges})
        return graph_dict

    def get_graph(self) -> GraphModel:
        graph_dict = self._read_to_dict()
        try:
            graph = GraphModel(**graph_dict)
            return graph
        except Exception as e:
            print(e)


if __name__ == "__main__":
    filename = "./maps/easy/02_simple_fork.txt"
    parser = Parser(filename)
    print(parser._hubs)
