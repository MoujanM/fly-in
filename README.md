*This project has been created as part of the 42 curriculum by mmirdama.*

# FLY-IN
Drone routing and visualization in Python

## Description

Fly-in is a Multi agent path finding problem (MAPF) conceptualized as a drone routing project, where the aim is to find the best conflict-free path from `start` to `goal` for a given number of drones and a map of zones and connections betweeen the set locations.

The program takes a map (example below), and outputs the steps needed to get all drones to their destination. The visualizer tracks the number of drones at each point as they move through their paths, demonstrating algorithm's respect for capacity rules.

### Algorithm choices and implementation strategy

Fly-in uses a two-level pathfinding strategy. First, a time-expanded A* search finds a route for each drone. Each search state contains both a hub and a timestamp, which allows the solver to model waiting, restricted zones that take two turns to cross, and normal or priority zones with lower movement cost. A Manhattan-distance heuristic based on hub coordinates guides the search toward the destination, while blocked zones are excluded from the available moves.

The multi-agent solver uses Conflict-Based Search (CBS) to combine the individual routes. It detects conflicts when drones exceed a hub's capacity at the same time or occupy the same connection during overlapping intervals. For each conflict, CBS adds a time-and-position constraint for the affected drone, reruns its low-level A* search, and stores the resulting plan in a priority queue ordered by total cost. This separates route finding from conflict resolution and produces a coordinated plan that respects map capacities. The final result reports the movement plan, each drone's cost, the total cost, and the makespan.

### Visual representation and user experience

The Pygame visualizer presents the map as a connected graph: hubs are colored rounded rectangles, connections are drawn between them, and capacity labels are shown for both hubs and links. Hub names and capacities make the map's rules visible while the simulation is running, so users can relate the solver's decisions to the underlying puzzle.

At each turn, drones are represented by count badges on their current hub. Drones traveling across a connection are displayed at the connection's midpoint, making multi-turn movement visible rather than appearing as an unexplained jump. A turn counter shows the current turn, the total number of turns, and the number of drones. Users can advance one turn at a time with `Space` to inspect the plan or press `E` to view its completed state, providing both detailed debugging and a quick overview of the solution.


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

When prompted, enter the path to a map file. For example:

```text
maps/easy/01_linear_path.txt
```

The solver calculates conflict-free routes for all drones and opens the visualization window. In the visualizer:

- Press `Space` to advance one turn.
- Press `E` to jump to the end of the simulation.
- Close the window to finish and print the simulation summary.

The summary includes each turn's movements, the makespan, the cost per agent, and the total cost.

### Map format

Map files are plain text files containing a drone count, one start hub, one end hub, hubs, and connections. Hubs can include zone and capacity metadata, while connections can include link capacity metadata. Existing examples are organized in `maps/easy`, `maps/medium`, `maps/hard`, and `maps/challenger`.

### Development commands

```sh
make debug  # Run with the Python debugger
make lint   # Run flake8 and mypy
make clean  # Remove Python caches and temporary compiled files
```

The pathfinding implementation uses A* for individual drone routes and Conflict-Based Search to resolve hub and connection conflicts while respecting capacity constraints.


## Resources
- [MAPF solutions overview](https://www.researchgate.net/publication/348716625_Survey_of_the_Multi-Agent_Pathfinding_Solutions)
- [Conflict-Based Search Algorithm](https://www.cse.iitk.ac.in/users/cs365/2013/hw2/sharon-stern-12_multi-agent-path-finding-conflict-based.pdf)
- [Intro to PyGame](https://eng.libretexts.org/Bookshelves/Computer_Science/Programming_Languages/Making_Games_with_Python_and_Pygame_(Sweigart)/03%3A_Pygame_Basics/3.14%3A_Primitive_Drawing_Functions)
- [PyGame Documentation](https://www.pygame.org/docs/)