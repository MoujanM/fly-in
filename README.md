*This project has been created as part of the 42 curriculum by mmirdama.*

# FLY-IN
Drone routing and visualization in Python

## Description

Fly-in is a Multi-agent Path Finding (MAPF) project presented as a drone-routing simulation. It finds a coordinated path from `start` to `goal` for a given number of drones on a graph of hubs and connections, while respecting hub capacity and timing constraints.

The program parses a map file, computes a conflict-free plan, and opens an interactive Pygame visualization. The simulation displays the number of drones at each hub or in transit on a connection, while the terminal summary reports the makespan and cost for each agent.

### Algorithm choices and implementation strategy

Fly-in uses a two-level pathfinding strategy. First, a time-expanded A* search finds a route for each drone. Each search state contains a hub and a timestamp, which allows the solver to model waiting, restricted zones that take two turns to cross, and normal or priority zones that take one turn to enter. A Manhattan-distance heuristic based on hub coordinates guides the search toward the destination, while blocked zones are excluded from available moves. The search also accepts time-and-position constraints so an individual route can be recalculated around an existing conflict.

The multi-agent solver uses Conflict-Based Search (CBS) to combine the individual routes. It detects conflicts when drones exceed a hub's capacity at the same time or occupy the same connection during overlapping intervals. For each conflict, CBS adds a time-and-position constraint for the excess drone, reruns its low-level A* search, and stores the resulting plan in a priority queue ordered by total cost. The search stops after 100 high-level iterations if no solution has been found. A successful result contains the joint movement plan, each drone's cost, the total cost, and the makespan.

### Visual representation and user experience

The Pygame visualizer presents the map as a connected graph: hubs are colored rounded rectangles, connections are drawn between them, and hub capacity labels are shown beside the hubs. Hub names and capacities make the map's rules visible while the simulation is running, so users can relate the solver's decisions to the underlying puzzle.

At each turn, drones are represented by count badges on their current hub. Drones traveling across a connection are displayed at the connection's midpoint, making multi-turn movement visible rather than appearing as an unexplained jump. A turn counter shows the current turn, the total number of turns, and the number of drones. The view supports the following controls:

- Press `Space` to advance one scheduled turn.
- Press `E` to jump to the completed state.
- Hold the arrow keys to pan the camera.
- Press `R` to recenter the camera and reset zoom.
- Use the mouse wheel to zoom between 0.1x and 5x.
- Close the window to stop the simulation and print its summary.


## Instructions

### Requirements

- Python 3.13 or newer
- `uv` for dependency and virtual-environment management
- A graphical environment for the Pygame visualizer

### Installation

Install the project dependencies with:

```sh
make install
```

The `install` target installs `uv` automatically when it is not already available, then runs `uv sync`.

### Running the simulation

Start the application with:

```sh
make run
```

Pass the path to a map file as the positional argument. For example:

```text
maps/easy/01_linear_path.txt
```

The solver parses the map, calculates conflict-free routes for all drones, and opens the visualization window. In the visualizer:

- Press `Space` to advance one turn.
- Press `E` to jump to the end of the simulation.
- Use the arrow keys to pan, the mouse wheel to zoom, and `R` to reset the view.
- Close the window to finish and print the simulation summary.

The summary includes each turn's movements, the makespan, the cost per agent, and the total cost.

### Map format

Map files are plain text files. Blank lines and lines beginning with `#` are ignored. The first meaningful line must define the number of drones, followed by hub and connection declarations:

```text
nb_drones: 2
start_hub: start 0 0 [color=green max_drones=2]
hub: middle 1 0 [zone=restricted color=orange]
end_hub: goal 2 0 [color=red max_drones=2]
connection: start-middle
connection: middle-goal
```

Hub declarations use `<kind>: <name> <x> <y> [metadata]`, where `kind` is `start_hub`, `hub`, or `end_hub`. Supported hub metadata includes `zone`, `color`, and `max_drones`. Zones are `normal`, `priority`, `restricted`, and `blocked`; restricted hubs take two turns to enter, while blocked hubs cannot be entered. Connection declarations use `connection: <hub_a>-<hub_b>` and may include `max_link_capacity` metadata. The parser validates hub names, references, duplicate connections, and the requirement for exactly one start and one end hub before creating the graph model.

Existing examples are organized in `maps/easy`, `maps/medium`, `maps/hard`, and `maps/challenger`.

### Development commands

```sh
make debug  # Run with the Python debugger
make lint   # Run flake8 and mypy
make clean  # Remove Python caches and temporary compiled files
```

The pathfinding implementation uses time-expanded A* for individual drone routes and Conflict-Based Search to resolve hub-capacity and connection-overlap conflicts. A* can wait at a hub, account for zone movement costs, and avoid CBS constraints. CBS applies each accumulated constraint set, recomputes the agents' paths, and chooses the lowest-total-cost plan from its search queue.


## Resources
- [MAPF solutions overview](https://www.researchgate.net/publication/348716625_Survey_of_the_Multi-Agent_Pathfinding_Solutions)
- [Conflict-Based Search Algorithm](https://www.cse.iitk.ac.in/users/cs365/2013/hw2/sharon-stern-12_multi-agent-path-finding-conflict-based.pdf)
- [Intro to PyGame](https://eng.libretexts.org/Bookshelves/Computer_Science/Programming_Languages/Making_Games_with_Python_and_Pygame_(Sweigart)/03%3A_Pygame_Basics/3.14%3A_Primitive_Drawing_Functions)
- [PyGame Documentation](https://www.pygame.org/docs/)