from src.models import Hub, Edge, GraphModel, ParsingError
from pydantic import ValidationError
import re
from typing import cast, Literal

# constant mod variables for efficient parsing
# naming captured groups using (?P<name>pattern)
HUB_PATTERN: re.Pattern = re.compile(r'^(?P<kind>\w+_hub|hub):\s+'
                                     r'(?P<name>\w+)\s+'
                                     r'(?P<x>-?\d+)\s+(?P<y>-?\d+)'
                                     r'(?:\s+\[(?P<meta>[^\]]*)\])?$')
EDGE_PATTERN: re.Pattern = re.compile(
    r'^connection:\s+(?P<hub_a>\w+)-(?P<hub_b>\w+)'
    r'(?:\s+\[(?P<meta>[^\]]*)\])?$')

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
            raise ParsingError(f"Malformed metadata: {metadata}\n \
                               Expected format:\n[zone=...][color=...] for \
                                hubs\n[max_link_capacity=...] for connections")
        return dict(metadata_list)

    def parse_return_hub(self, hub_str: str) -> Hub:
        """
        Function that takes a string. tries to match with hub_pattern.
        if there is a match, returns Hub object.
        """
        m: re.Match | None = HUB_PATTERN.match(hub_str)
        if not m:
            raise ParsingError(f"Malformed hub line: {hub_str}\n \
                               Expected format: <kind>: <name> <x> \
                               <y> [metadata]")

        metadata: dict[str, str] = {}
        if m.group('meta'):
            metadata = self.parse_meta(m.group('meta'))
            zone = metadata.get('zone')
            if zone and zone not in ['normal',
                                     'restricted', 'priority', 'blocked']:
                raise ParsingError(f"Invalid zone type: {metadata['zone']}")
        try:
            new_hub = Hub(
                kind=m.group('kind'),
                name=m.group('name'),
                x=int(m.group('x')),
                y=int(m.group('y')),
                zone=cast(Literal['normal', 'restricted',
                                  'priority', 'blocked'],
                          metadata.get('zone', 'normal')),
                color=str(metadata.get('color')),
                max_drones=int(metadata.get('max_drones', 1)))
            return new_hub
        except ValidationError as e:
            raise e

    def parse_return_edge(self, edge_str) -> Edge:
        m: re.Match | None = EDGE_PATTERN.match(edge_str)
        if not m:
            raise ParsingError(f"Malformed connection line: {edge_str}\n \
                               Expected format: connection: <name1>-<name2> \
                               [metadata]")

        hub_name_lookup: dict[str, Hub] = {h.name: h for h in self._hubs}
        hub_b: Hub | None = hub_name_lookup.get(m.group('hub_b'))
        hub_a: Hub | None = hub_name_lookup.get(m.group('hub_a'))

        if not hub_a or not hub_b:
            raise ParsingError(f"Connection seems invalid: {edge_str}")

        edge_name: str = f"{hub_a.name}-{hub_b.name}"
        metadata: dict[str, str] = {}
        if m.group('meta'):
            metadata = self.parse_meta(m.group('meta'))
        try:
            new_edge = Edge(
                name=edge_name,
                hub_a=hub_a,
                hub_b=hub_b,
                max_capacity=int(metadata.get('max_link_capacity', 1))
                )
            return new_edge
        except ValidationError as e:
            raise e

    def _read_raise_error(self) -> list[str]:
        valid: list[str] = ['start_hub', 'hub', 'end_hub', 'connection']
        lines: list[str] = []
        try:
            with open(self.filename) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    lines.append(line)
        except FileNotFoundError as e:
            raise e
        if not lines:
            raise ParsingError("Empty file.")
        if not lines[0].startswith('nb_drones'):
            raise ParsingError("First line must define number of agents \
                                with 'nb_drones: <positive_integer>'.")
        for line in lines[1:]:
            if not any(line.startswith(val) for val in valid):
                raise ParsingError(f"Bad line prefix in '{line}'\n \
                                   Must be one of {[val for val in valid]}")
        return lines

    def _read_values(self) -> tuple[int, list[Hub], list[Edge]]:
        """function to read and return the following:
        drone_count;
        all hubs (vertices) marking start/end;
        all connections (edges)
        """
        nb_agents: int = 0
        try:
            lines = self._read_raise_error()
        except Exception as e:
            raise e

        for line in lines:
            if line.startswith('nb_drones'):
                nb_agents = int(line.split(':')[1].strip())
            elif 'hub:' in line:
                try:
                    self.parse_return_hub(line)
                    self._hubs.append(self.parse_return_hub(line))
                except ValidationError as e:
                    for err in e.errors():
                        print(err['msg'])
            elif 'connection:' in line:
                try:
                    self.parse_return_edge(line)
                    self._edges.append(self.parse_return_edge(line))
                except ValidationError as e:
                    for err in e.errors():
                        print(err['msg'])
        return nb_agents, self._hubs, self._edges

    def get_graph(self) -> 'GraphModel':
        try:
            graph_vals = self._read_values()
        except Exception:
            raise

        try:
            return GraphModel(nb_agents=graph_vals[0],
                              hubs=graph_vals[1],
                              edges=graph_vals[2])
        except ValidationError as err:
            raise ParsingError(f"Graph validation failed:\n \
                               In {err.errors()[0]['loc']}: \
                                {err.errors()[0]['msg']}") from err


if __name__ == "__main__":
    filename = "parser_test.txt"
    try:
        parser = Parser(filename)
    except Exception as e:
        print(e)
    # print(parser._hubs)
