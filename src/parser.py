from structs import Hub, Edge
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
    def __init__(self) -> None:
        self._hubs: list[Hub] = []
        self._edges: list[Edge] = []
        self._graph: dict[str, int | list[Hub | Edge]] = {}

    def parse_meta(self, metadata: str) -> dict[str, str]:
        metadata_list: list = META_KV_PATTERN.findall(metadata)
        return dict(metadata_list)

    def parse_return_hub(self, hub_str: str) -> Hub | None:
        """
        Function that takes a string. tries to match with hub_pattern.
        if there is a match, returns Hub object.
        """
        m: re.Match = HUB_PATTERN.match(hub_str)
        if not m:
            return None
        metadata: dict[str, str] = {}
        if m.group('meta'):
            metadata = self.parse_meta(m.group('meta'))

        return Hub(
            kind=m.group('kind'),
            name=m.group('name'),
            x=int(m.group('x')),
            y=int(m.group('y')),
            zone=metadata.get('zone'),
            color=metadata.get('color'),
            max_drones=int(metadata.get('max_drones', 1))
        )

    def parse_return_edge(self, edge_str) -> Edge | None:
        m: re.Match = EDGE_PATTERN.match(edge_str)
        if not m:
            return None

        hub_name_lookup: dict[str, Hub] = {h.name: h for h in self._hubs}
        hub_a: Hub = hub_name_lookup.get(m.group('hub_a'))
        hub_b: Hub = hub_name_lookup.get(m.group('hub_b'))

        if not hub_a or not hub_b:
            raise Exception("Problem building edge - double check")

        metadata: dict[str, str] = {}
        if m.group('meta'):
            metadata = self.parse_meta(m.group('meta'))

        return Edge(hub_a,
                    hub_b,
                    max_capacity=int(metadata.get('max_link_capacity', 1)))

    def read_to_dict(self, path_to_file: str) -> dict[str, int | list[Hub | Edge]]:
        """function to read and return the following:
        drone_count;
        all hubs (vertices) marking start/end;
        all connections (edges)
        """
        nb_agents: int = None
        with open(path_to_file) as f:
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

        self._graph.update({'agents': nb_agents,
                            'hubs': self._hubs,
                            'edges': self._edges})
        return self._graph


if __name__ == "__main__":
    filename = "./maps/easy/01_linear_path.txt"
    parser = Parser()
    parser.read_to_dict(filename)
    print(parser._hubs)
