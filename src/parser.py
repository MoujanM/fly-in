from src.models import Hub, Edge, GraphModel, ParsingError
from pydantic import ValidationError
import re
from typing import cast, Literal

HUB_PATTERN: re.Pattern = re.compile(r'^(?P<kind>\w+_hub|hub):\s+'
                                     r'(?P<name>\w+)\s+'
                                     r'(?P<x>-?\d+)\s+(?P<y>-?\d+)'
                                     r'(?:\s+\[(?P<meta>[^\]]*)\])?$')
EDGE_PATTERN: re.Pattern = re.compile(
    r'^connection:\s+(?P<hub_a>\w+)-(?P<hub_b>\w+)'
    r'(?:\s+\[(?P<meta>[^\]]*)\])?$')

META_KV_PATTERN: re.Pattern = re.compile(r'(\w+)=(\w+|-?\d+)')


class GraphParser():
    """Parse a map file into a validated :class:`GraphModel`."""

    def __init__(self, filename: str) -> None:
        """Read and validate a map file immediately.

        Args:
            filename: Path to the map file.

        Returns:
            None.

        Raises:
            ParsingError: If the file contents are malformed or invalid.
            FileNotFoundError: If ``filename`` does not exist.
        """
        self.filename: str = filename
        self._hubs: list[Hub] = []
        self._edges: list[Edge] = []
        self._graph: GraphModel = self.get_graph()

    def parse_meta(self, metadata: str) -> dict[str, str]:
        """Parse key-value metadata inside a map declaration.

        Args:
            metadata: Metadata text without its surrounding brackets.

        Returns:
            Metadata keys and values as strings.

        Raises:
            ParsingError: If no valid key-value pairs are found.
        """
        metadata_list: list = META_KV_PATTERN.findall(metadata)
        if not metadata_list:
            raise ParsingError(f"Malformed metadata: {metadata}\n \
                               Expected format:\n[zone=...][color=...] for \
                                hubs\n[max_link_capacity=...] for connections")
        return dict(metadata_list)

    def parse_return_hub(self, hub_str: str) -> Hub:
        """Parse one hub declaration into a validated hub.

        Args:
            hub_str: Map-file line describing a hub.

        Returns:
            The parsed hub.

        Raises:
            ParsingError: If the line or its metadata is malformed.
            ValidationError: If the hub fields fail Pydantic validation.
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

    def parse_return_edge(self, edge_str: str) -> Edge:
        """Parse one connection declaration into a validated edge.

        Args:
            edge_str: Map-file line describing a connection.

        Returns:
            The parsed edge.

        Raises:
            ParsingError: If the line, metadata, or hub references are invalid.
            ValidationError: If the edge fields fail Pydantic validation.
        """
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
        """Read meaningful map lines and validate their prefixes.

        Returns:
            Non-empty, non-comment lines from the map file.

        Raises:
            ParsingError: If the file is empty or has an invalid structure.
            FileNotFoundError: If the map file does not exist.
        """
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
            raise ParsingError("First line must define number of agents "
                               "with 'nb_drones: <positive_integer>'.")
        for line in lines[1:]:
            if not any(line.startswith(val) for val in valid):
                raise ParsingError(f"Bad line prefix in '{line}'\n"
                                   f"Must be one of {[val for val in valid]}")
        return lines

    def _read_values(self) -> tuple[int, list[Hub], list[Edge]]:
        """Parse the map lines into a drone count, hubs, and edges.

        Returns:
            A tuple containing the drone count, parsed hubs, and parsed edges.

        Raises:
            ParsingError: If any declaration fails validation.
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
                    raise ParsingError(f"Hub validation failed:\nIn "
                                       f"{e.errors()[0]['loc']}: "
                                       f"{e.errors()[0]['msg']}") from e
            elif 'connection:' in line:
                try:
                    self.parse_return_edge(line)
                    self._edges.append(self.parse_return_edge(line))
                except ValidationError as e:
                    raise ParsingError(f"Edge validation failed:\n In "
                                       f"{e.errors()[0]['loc']}: "
                                       f"{e.errors()[0]['msg']}") from e
        return nb_agents, self._hubs, self._edges

    def get_graph(self) -> 'GraphModel':
        """Build the validated graph model from the parsed map values.

        Returns:
            A validated graph model.

        Raises:
            ParsingError: If graph-level validation fails.
        """
        try:
            graph_vals = self._read_values()
        except Exception:
            raise

        try:
            return GraphModel(nb_agents=graph_vals[0],
                              hubs=graph_vals[1],
                              edges=graph_vals[2])
        except ValidationError as err:
            raise ParsingError(f"Graph validation failed:\n In "
                               f"{err.errors()[0]['loc']}: "
                               f"{err.errors()[0]['msg']}") from err


if __name__ == "__main__":
    filename = "parser_test.txt"
    try:
        parser = GraphParser(filename)
    except Exception as e:
        print(e)
    # print(parser._hubs)
