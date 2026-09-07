from src.cli import CLIParser
from src.parser import GraphParser
from src.models import CBSResult, GraphModel
from src.cbs import CBS
from visualizer.map import Map
from visualizer.agents import Agents
from controller import SimController
import pygame
import sys


class FlyIn():
    def __init__(self):
        try:
            self.graph = self._run_checks()
        except Exception as e:
            print(e)
        self.running: bool = False

    def _run_checks(self) -> GraphModel | None:
        p = CLIParser()
        puzzle = p.args.input_map
        try:
            parser = GraphParser(puzzle)
            return parser._graph
        except Exception as e:
            print(e)
            sys.exit(1)

    def run_sim(self) -> None:
        solver = CBS(self.graph)
        result = solver.solve()
        if not result:
            return
        control = SimController(self.graph, result)
        static = Map(self.graph)
        dynamic = Agents(self.graph)
        pygame.init()
        pygame.font.init()
        display = pygame.display.set_mode(static._screen)
        pygame.display.set_caption("FLY-IN")
        clock = pygame.time.Clock()
        self.run_loop(control, display, static, dynamic, clock)
        self.print_summary(result)
        return None

    def run_loop(self, control: SimController,
                 display: pygame.Surface, static: Map,
                 dynamic: Agents, clock: pygame.time.Clock) -> None:
        self.running = True
        while self.running:
            # 1. event handling
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and control.current_turn != control.max_turn:
                        control.advance_turn()
                    if event.key == pygame.K_e:
                        control.jump_to_end()
                if event.type == pygame.QUIT:
                    self.running = False
            # 2. get state
            if control.sim_complete:
                turn_state = control.final_state()
            else:
                turn_state = control.get_turn_state()
            turn_header = control.turn_header()

            # 3. draw from scratch
            display.fill("grey")
            static._draw_edges(display)
            static._draw_hubs(display)
            dynamic._turn_blits(display, turn_state)
            dynamic._turn_counter(display, turn_header)
            pygame.display.update()
            clock.tick(60)
        pygame.quit()
        return None

    def print_summary(self, result: CBSResult) -> None:
        print(f"Makespan: {result.makespan}")
        print(f"Cost per agent: {result.cost_per_agent}")
        print(f"Total cost: {result.total_cost}")
        return None
        

if __name__ == "__main__":
    program = FlyIn()
    program.run_sim()

