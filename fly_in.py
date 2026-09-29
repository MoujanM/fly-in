from src.cli import CLIParser
from src.parser import GraphParser
from src.models import GraphModel
from src.cbs import CBS
from visualizer.renderer import Renderer
from visualizer.map import Map
from visualizer.agents import Agents
from controller import SimController
import argparse
import pygame
import sys
import os
from subprocess import call


class FlyIn:
    """Coordinate map loading, solving, and graphical simulation."""

    def __init__(self) -> None:
        """Load the requested map and prepare the solver and renderer.

        Returns:
            None.
        """
        try:
            self._args, self.graph = self._run_checks()
        except Exception as e:
            print(e)
        self.running: bool = False

        self.solver = CBS(self.graph)
        self.result = self.solver.solve()
        self.renderer = Renderer(self.graph)
        # if not result:
        #     return

    def _run_checks(self) -> tuple[argparse.Namespace, GraphModel]:
        """Parse and validate the map selected on the command line.

        Returns:
            - Parsed arguments
            - The validated graph model.

        Raises:
            SystemExit: If the input map cannot be parsed.
        """
        p = CLIParser()
        puzzle = p.args.input_map
        try:
            parser = GraphParser(puzzle)
            return p.args, parser._graph
        except Exception as e:
            print(e)
            sys.exit(1)

    def run_sim(self) -> None:
        """Initialize Pygame and run the interactive simulation.

        Returns:
            None.
        """
        if not self.result:
            return
        control = SimController(self.graph, self.result)
        static = Map(self.graph)
        dynamic = Agents(self.graph)
        pygame.init()
        pygame.font.init()
        display = pygame.display.set_mode(self.renderer.display_size)
        pygame.display.set_caption("FLY-IN")
        clock = pygame.time.Clock()
        self.run_loop(control, display, static, dynamic, clock)
        self.print_summary(control)
        return None

    def run_loop(self, control: SimController,
                 display: pygame.Surface, static: Map,
                 dynamic: Agents, clock: pygame.time.Clock) -> None:
        """Process input and redraw the simulation until the window closes.

        Args:
            control: Simulation state controller.
            display: Pygame surface used for drawing.
            static: Renderer for hubs and connections.
            dynamic: Renderer for agent positions and turn status.
            clock: Pygame clock that limits the frame rate.

        Returns:
            None.
        """
        self.running = True
        while self.running:
            keys = pygame.key.get_pressed()
            pan_speed = 15 / max(0.1, self.renderer.zoom)
            if keys[pygame.K_LEFT]:
                self.renderer.camera_x += pan_speed
            if keys[pygame.K_RIGHT]:
                self.renderer.camera_x -= pan_speed
            if keys[pygame.K_UP]:
                self.renderer.camera_y += pan_speed
            if keys[pygame.K_DOWN]:
                self.renderer.camera_y -= pan_speed
            if keys[pygame.K_r]:
                (self.renderer.camera_x,
                 self.renderer.camera_y) = self.renderer._init_camera()
                self.renderer.zoom = 1.0
            # 1. event handling
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if (event.key == pygame.K_SPACE):
                        if control.current_turn < control.max_turn:
                            control.advance_turn()
                            output = control.output.get(
                                     control.current_turn - 1)
                            if output:
                                for o in output:
                                    print(o)
                        elif control.current_turn == control.max_turn:
                            continue
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                if event.type == pygame.MOUSEWHEEL:
                    z_factor: float = 1.1 if event.y > 0 else 0.9
                    self.renderer.zoom_point(z_factor)
                if event.type == pygame.QUIT:
                    self.running = False
            # # 2. get state
            # if control.current_turn == control.max_turn:
            #     turn_state = control.final_state()
            # else:
            #     turn_state = control.get_turn_state()
            turn_header = control.turn_header()
            turn_state = control.get_turn_state()

            # 3. draw from scratch
            display.fill("grey19")
            static._draw_edges(display, self.renderer)
            static._draw_hubs(display, self.renderer)
            dynamic._turn_blits(display, self.renderer, turn_state)
            dynamic._turn_counter(display, self.renderer, turn_header)
            pygame.display.update()
            clock.tick(60)
        pygame.quit()
        return None

    def print_summary(self, control: SimController) -> None:
        """Print makespan and cost information for a completed plan.
        Args:
            control: Simulation state controller.
        Returns:
            None.
        """
        _ = call('clear' if os.name == 'posix' else 'cls')
        for turn, desc in control.output.items():
            for d in desc:
                if d:
                    print(d)

        if self._args.verbose:
            print(f"Makespan: {control.result.makespan}")
            print(f"Total cost: {control.result.total_cost}")

        if self._args.cost_per_agent:
            print("Cost per agent:")
            for agent, cost in control.result.cost_per_agent.items():
                print(f"{agent}: {cost}")
        return None


if __name__ == "__main__":
    program = FlyIn()
    program.run_sim()
