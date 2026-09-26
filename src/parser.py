from src.models import Hub, Edge, GraphModel, ParsingError
from pydantic import ValidationError
import re
from typing import cast, Literal

HUB_PATTERN: re.Pattern = re.compile(r'^(?P<kind>\w+_hub|hub):\s+'
                                     r'(?P<name>[\w-]+)\s+'
                                     r'(?P<x>-?\d+)\s+(?P<y>-?\d+)'
                                     r'(?:\s+\[(?P<meta>[^\[\]]*)\])?$')
EDGE_PATTERN: re.Pattern = re.compile(
    r'^connection:\s+(?P<hub_a>\w+)-(?P<hub_b>\w+)'
    r'(?:\s+\[(?P<meta>[^\[\]]*)\])?$')

META_KV_PATTERN: re.Pattern = re.compile(r'(\w+)=(\w+|-?\d+)')

VALID_HUB_META    = {'zone', 'color', 'max_drones'}
VALID_EDGE_META   = {'max_link_capacity'}


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

    def parse_meta(self, metadata: str, lineno: int,
               known_keys: set[str] | None = None) -> dict[str, str]:
        pairs = META_KV_PATTERN.findall(metadata)
        if not pairs:
            raise ParsingError(
                f"Line {lineno}: metadata '[{metadata}]' contains "
                f"no valid key=value pairs."
            )
        result = dict(pairs)
        if known_keys is not None:
            unknown = set(result.keys()) - known_keys
            if unknown:
                raise ParsingError(
                    f"Line {lineno}: unknown metadata key(s) {unknown}. "
                    f"Valid keys are: {known_keys}."
                )
        return result

    def parse_return_hub(self, hub_str: str, lineno: int) -> Hub:
        """Parse one hub declaration into a validated hub."""
        m = HUB_PATTERN.match(hub_str)
        if not m:
            raise ParsingError(
                f"Line {lineno}: malformed hub declaration: '{hub_str}'. "
                f"Expected: <kind>: <name> <x> <y> [metadata]"
            )

        metadata: dict[str, str] = {}
        if m.group('meta'):
            metadata = self.parse_meta(m.group('meta'), lineno,
                        known_keys={'zone', 'color', 'max_drones'})

        kind = m.group('kind')
        name = m.group('name')
        if '-' in name:
            raise ParsingError(
                f"Line {lineno}: hub names cannot contain dashes.")

        # validate zone type before Pydantic sees it
        zone_raw = metadata.get('zone', 'normal')
        valid_zones = ('normal', 'restricted', 'priority', 'blocked')
        if zone_raw not in valid_zones:
            raise ParsingError(
                f"Line {lineno}: invalid zone type '{zone_raw}' "
                f"for hub '{name}'. Must be one of {valid_zones}."
            )

        # validate capacity — only meaningful for regular hubs
        max_drones: int | None = None
        if kind == 'hub':
            raw_cap = metadata.get('max_drones', 1)
            try:
                cap = int(raw_cap)
                if cap < 1:
                    raise ValueError
                max_drones = cap
            except ValueError:
                raise ParsingError(
                    f"Line {lineno}: max_drones must be a positive integer, "
                    f"got '{raw_cap}' for hub '{name}'."
                )

        # set default colour and manage special case in challenger
        color = metadata.get('color') or "white"

        try:
            return Hub(
                kind=cast(Literal['start_hub', 'hub', 'end_hub'], kind),
                name=name,
                x=int(m.group('x')),
                y=int(m.group('y')),
                zone=cast(Literal['normal', 'restricted', 'priority', 'blocked'],
                      zone_raw),
                color=color,
                max_drones=max_drones,
            )
        except ValidationError as e:
            field = e.errors()[0]['loc']
            msg = e.errors()[0]['msg']
            raise ParsingError(f"Line {lineno}: hub '{name}' failed validation "
                            f"on field {field}: {msg}") from e

    def parse_return_edge(self, edge_str: str, lineno: int) -> Edge:
        """Parse one connection declaration into a validated edge."""
        m = EDGE_PATTERN.match(edge_str)
        if not m:
            raise ParsingError(
                f"Line {lineno}: malformed connection declaration: '{edge_str}'. "
                f"Expected: connection: <name_a>-<name_b> [metadata]"
            )

        hub_lookup: dict[str, Hub] = {h.name: h for h in self._hubs}
        a_name, b_name = m.group('hub_a'), m.group('hub_b')

        if a_name not in hub_lookup:
            raise ParsingError(
                f"Line {lineno}: connection references undefined hub '{a_name}'."
            )
        if b_name not in hub_lookup:
            raise ParsingError(
                f"Line {lineno}: connection references undefined hub '{b_name}'."
            )

        hub_a, hub_b = hub_lookup[a_name], hub_lookup[b_name]

        metadata: dict[str, str] = {}
        if m.group('meta'):
            metadata = self.parse_meta(m.group('meta'), lineno,
                        known_keys={'max_link_capacity'})

        raw_cap = metadata.get('max_link_capacity', '1')
        try:
            cap = int(raw_cap)
            if cap < 1:
                raise ValueError
        except ValueError:
            raise ParsingError(
                f"Line {lineno}: max_link_capacity must be a positive integer, "
                f"got '{raw_cap}'."
            )

        try:
            return Edge(
                name=f"{a_name}-{b_name}",
                hub_a=hub_a,
                hub_b=hub_b,
                max_capacity=cap,
            )
        except ValidationError as e:
            field = e.errors()[0]['loc']
            msg = e.errors()[0]['msg']
            raise ParsingError(
                f"Line {lineno}: connection '{a_name}-{b_name}' failed "
                f"validation on field {field}: {msg}"
            ) from e

    def _read_lines(self) -> list[tuple[int, str]]:
        """Read file, strip blanks/comments,
            return (original_line_no, content)."""
        lines: list[tuple[int, str]] = []
        try:
            with open(self.filename) as f:
                for lineno, raw in enumerate(f, start=1):
                    stripped = raw.strip()
                    if not stripped or stripped.startswith('#'):
                        continue
                    lines.append((lineno, stripped))
        except FileNotFoundError:
            raise

        if not lines:
            raise ParsingError("Line 0: file is empty.")

        lineno, first = lines[0]
        if not first.startswith('nb_drones:'):
            raise ParsingError(
                f"Line {lineno}: first meaningful line must be "
                f"'nb_drones: <positive_integer>', got: '{first}'"
            )

        valid_prefixes = ('nb_drones:', 'start_hub:', 'end_hub:', 'hub:', 'connection:')
        for lineno, line in lines[1:]:
            if not any(line.startswith(p) for p in valid_prefixes):
                raise ParsingError(
                    f"Line {lineno}: unrecognised line prefix in '{line}'. "
                    f"Expected one of: {valid_prefixes}"
                )

        return lines

    def _read_values(self) -> tuple[int, list[Hub], list[Edge]]:
        """Parse the map lines into a drone count, hubs, and edges."""
        lines = self._read_lines()   # list[tuple[int, str]]
        nb_agents: int = 0
        seen_edges: set[frozenset[str]] = set()   # for duplicate detection

        for lineno, line in lines:
            if line.startswith('nb_drones:'):
                try:
                    nb_agents = int(line.split(':', 1)[1].strip())
                    if nb_agents < 1:
                        raise ValueError
                except ValueError:
                    raise ParsingError(
                        f"Line {lineno}: nb_drones must be a positive integer."
                    )

            elif line.startswith(('start_hub:', 'hub:', 'end_hub:')):
                hub = self.parse_return_hub(line, lineno)
                # unique name check
                if any(h.name == hub.name for h in self._hubs):
                    raise ParsingError(
                        f"Line {lineno}: duplicate hub name '{hub.name}'."
                    )
                self._hubs.append(hub)

            elif line.startswith('connection:'):
                edge = self.parse_return_edge(line, lineno)
                # duplicate connection check (a-b == b-a)
                pair = frozenset([edge.hub_a.name, edge.hub_b.name])
                if pair in seen_edges:
                    raise ParsingError(
                        f"Line {lineno}: duplicate connection "
                        f"'{edge.hub_a.name}-{edge.hub_b.name}' "
                        f"(or its reverse) already defined."
                    )
                seen_edges.add(pair)
                self._edges.append(edge)
            else:
                raise ParsingError(f"Line {lineno}: Unknown line start, could not parse.")
        return nb_agents, self._hubs, self._edges

    def get_graph(self) -> GraphModel:
        """Build the validated graph model from the parsed map values.

        Returns:
            A validated graph model."""

        nb_agents, hubs, edges = self._read_values()

        try:
            return GraphModel(nb_agents=nb_agents, hubs=hubs, edges=edges)
        except ValidationError as e:
            # field = e.errors()[0]['loc']
            msg   = e.errors()[0]['msg']
            raise ParsingError(
                f"Graph validation failed on {msg}"
            ) from e

if __name__ == "__main__":
    filename = "maps/easy/01_linear_path.txt"
    try:
        parser = GraphParser(filename)
        print(parser._graph)
    except Exception as e:
        print(e)
    
