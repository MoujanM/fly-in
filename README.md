*This project has been created as part of the 42 curriculum by mmirdama.*

# FLY-IN 🚁

> Multi-agent drone routing simulation with interactive visualisation

---

## Description

Fly-in is a Multi-Agent Path Finding (MAPF) project implemented as a drone-routing simulator. Given a map of hubs and connections, the program finds a coordinated, conflict-free path for a fleet of drones from a single `start_hub` to a shared `goal_hub`, respecting per-hub capacity limits, connection capacity limits, and zone-type movement costs.

The program parses a plain-text map file, solves the routing problem using a two-level algorithm, and opens an interactive Pygame window showing the simulation turn by turn. When the window is closed, the terminal prints a full movement summary.

---

## Algorithm Choices and Implementation Strategy

### Low-level search — Time-expanded A\*

Each drone's individual route is planned using a **time-expanded A\* search**. Rather than treating the graph as a static set of locations, the search state is a pair `(hub, timestep)`, which allows the solver to model:

- **Waiting** — staying at a hub for one turn when movement is blocked or suboptimal.
- **Zone costs** — entering a `normal` or `priority` hub costs 1 turn; entering a `restricted` hub costs 2 turns and commits the drone to a connection for the intermediate turn.
- **Blocked zones** — hubs marked `blocked` are excluded from available moves.
- **Constraints** — the search accepts a set of `(position, timestep)` prohibitions injected by the high-level solver, so a drone's route can be recalculated around an existing conflict.

A Manhattan-distance heuristic (with a small ±0.1 tie-breaking bias for priority and restricted zones) guides expansion toward the goal while keeping the heuristic admissible.

### High-level search — Conflict-Based Search (CBS)

Individual routes are combined into a joint plan using **Conflict-Based Search**. CBS operates on a priority queue of *constraint nodes*, each representing a complete multi-agent plan under a specific set of constraints. At each iteration:

1. The cheapest node is popped from the queue.
2. The joint plan is checked for conflicts:
   - **Hub conflicts** — more drones occupying a hub at the same timestep than `max_drones` permits.
   - **Edge conflicts** — drones whose restricted-zone traversal intervals overlap on the same connection, exceeding `max_link_capacity`.
3. If no conflict exists, the plan is returned as the solution.
4. Otherwise, a constraint is added for each excess agent at the conflicting position and time, the affected routes are replanned, and a new node is pushed onto the queue.

This guarantees that capacity constraints at both hubs and connections are respected, and that drones committed to a restricted-zone transit cannot be diverted mid-connection.

---

## Visual Representation

The Pygame visualiser renders the map as a connected graph and updates it turn by turn.

| Feature | Detail |
|---|---|
| Hubs | Colored zones matching map metadata; each bearing name, zone and capacity captions |
| Edges | Connection capacity shown at the midpoint if value greater than 1 (default) |
| Drone badges | Count badge on each occupied hub each turn |
| In-transit drones | Badge shown at the edge midpoint during restricted-zone traversal |
| Turn counter | Current turn, total turns, and active drone count displayed at the bottom of screen |
| Camera controls | Pan, zoom, and reset — see Controls below |

Displaying drones at the connection midpoint during multi-turn movement makes the restricted-zone mechanic visible rather than appearing as an unexplained gap in a drone's journey. Capacity labels let users relate the solver's decisions to the map's rules without consulting the source file.

### Controls

| Key / Input | Action |
|---|---|
| `Space` | Advance one turn |
| `Esc` | End visualisation and print summary |
| Arrow keys (hold) | Pan the camera |
| Mouse wheel | Zoom in / out (0.1× – 5×) |
| `R` | Reset camera and zoom |
| Close window | End visualisation and print summary |

---

## Instructions

### Requirements

- Python **3.13** or newer
- [`uv`] for dependency and virtual-environment management
- A graphical environment capable of opening a Pygame window

### Installation

```sh
make install
```

This installs `uv` if it is not already available, then runs `uv sync` to create a virtual environment and install all dependencies.

### Running the simulation

```sh
make run
```

The solver parses the map, computes conflict-free routes, and opens the visualisation window. Close the window to print the movement summary. 

The `make` command loads a default map passed as a required argument. The program also accepts command-line flags directly:

```sh
uv run -m fly_in [--verbose] [--cost-per-agent] <map>
```

| Flag | Effect |
|---|---|
| `--verbose` | Print makespan and total cost after the movement summary |
| `--cost-per-agent` | Print individual cost for each drone |

Example:

```sh
uv run fly_in.py --verbose --cost-per-agent maps/medium/02_circular_loop.txt
```

---

## Map Format

Map files are plain text. Strict parsing rules are enforced, if a line contains malformed or unexpected input, `ParsingError` is raised, displaying the problematic line number. Blank lines and lines beginning with `#` are ignored, the first meaningful line must declare the drone count, subsequent lines must follow expected format for hub and connection details.

```text
# Example map
nb_drones: 2

start_hub: start 0 0 [color=green max_drones=2]
hub:       middle 1 0 [zone=restricted color=orange]
end_hub:   goal   2 0 [color=red max_drones=2]

connection: start-middle
connection: middle-goal
```

### Hub and Edge declaration

```
<kind>: <name> <x> <y> [metadata]
```

| Field | Values |
|---|---|
| `kind` | `start_hub`, `hub`, `end_hub` |
| `name` | Unique identifier — no hyphens |
| `x`, `y` | Integer grid coordinates |
| `zone` | `normal` (default), `priority`, `restricted`, `blocked` |
| `color` | Any Pygame-recognised colour name (defaults to white) |
| `max_drones` | Maximum simultaneous occupants (default: 1) |

### Connection declaration

```
connection: <hub_a>-<hub_b> [max_link_capacity=N]
```

The parser validates that both hub names exist, that connections are not duplicated, and that exactly one `start_hub` and one `end_hub` are present.

Errors raise a `ParsingError` with a descriptive message before any solving begins.

---

## Example Input and Output

**Map** — `maps/easy/01_linear_path.txt`

```text
nb_drones: 2

start_hub: start     0 0 [color=green max_drones=2]
hub:       waypoint1 1 0 [color=blue]
hub:       waypoint2 2 0 [color=blue]
end_hub:   goal      3 0 [color=red max_drones=2]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
```

**Terminal output** (with `--verbose`):

```text
D1-waypoint1 D2-waypoint1
D1-waypoint2 D2-waypoint2
D1-goal D2-goal
Makespan: 3
Total cost: 6
```

Each line represents one simulation turn. Drones that do not move in a given turn are omitted. A drone that has reached the goal is no longer tracked.

For a restricted-zone map, in-transit moves appear in the format `D1-start-loop_a` (drone identifier, origin, destination) to indicate the drone is occupying the connection during that turn.

---

## Project Structure

```
fly-in/
├── src/
│   ├── cli.py           # argparse to manage program arguments
│   ├── models.py        # Pydantic data models (Hub, Edge, GraphModel, PathStep …)
│   ├── parser.py        # Map file parser and validator
│   ├── singlepath.py    # Time-expanded A* and path reconstruction
│   └── cbs.py           # Conflict-Based Search solver
├── visualizer/
│   ├── renderer.py      # Base renderer (scale, camera, coordinate transforms)
│   ├── map.py           # Static map drawing (hubs, edges, captions)
│   └── agents.py        # Dynamic drone badges and turn counter
├── controller.py        # Simulation state manager (turn map, positions, output)
├── fly_in.py            # Entry point and argument parsing
├── maps/                # Bundled puzzle maps (easy / medium / hard / challenger)
└── Makefile
```

---

## Resources

### Algorithms and theory

- Sharon, G., Stern, R., Felner, A., & Sturtevant, N. (2015). [Conflict-based search for optimal multi-agent pathfinding](https://www.sciencedirect.com/science/article/pii/S0004370214001386)
- Stern, R. et al. (2019). [Multi-Agent Pathfinding: Definitions, Variants, and Benchmarks](https://www.researchgate.net/publication/348716625_Survey_of_the_Multi-Agent_Pathfinding_Solutions) — MAPF survey covering CBS and related algorithms.
- Red Blob Games — [Introduction to A\*](https://www.redblobgames.com/pathfinding/a-star/introduction.html) — accessible visual explanation of A* and heuristics.
- [CBS algorithm — IIT Kanpur course material](https://www.cse.iitk.ac.in/users/cs365/2013/hw2/sharon-stern-12_multi-agent-path-finding-conflict-based.pdf)

### Libraries

- [Pygame documentation](https://www.pygame.org/docs/)
- [Pydantic documentation](https://docs.pydantic.dev/)
- [Python `heapq` module](https://docs.python.org/3/library/heapq.html)
- [Python `re` module — Regular expression HOWTO](https://docs.python.org/3/howto/regex.html)

### AI usage

Claude (Anthropic) was used throughout this project as a pair-programming and tutoring tool. Specific uses included:

- **Algorithm design** — conceptual explanations of time-expanded A\*, CBS tree structure, conflict detection, and constraint propagation; the underlying logic was implemented independently after discussion.
- **Regex parsing** — tutorial on named capture groups and non-capturing groups for the map file parser.
- **Pygame visualiser** — conceptual explanation of the game loop, coordinate transform pipeline (logical → world → screen), camera/zoom design, and blit ordering; code was written independently.
- **Code review** — structural feedback on class responsibilities, separation of concerns between solver, controller, and visualiser layers.

All algorithmic implementations, data structures, and final code are the author's own work. AI was not used to generate complete implementations directly.