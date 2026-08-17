from src.parser import Parser
from src.cbs import CBS
from src.models import CBSResult
from visualizer.map import Map
from visualizer.agents import Agents
from controller import SimController
import pygame

def main():
    map_files = ["./maps/hard/01_maze_nightmare.txt",
                 "./maps/hard/02_capacity_hell.txt",
                 "./maps/hard/03_ultimate_challenge.txt",
                 "./maps/medium/02_circular_loop.txt"
    ]

    my_map = map_files[3]
    parser = Parser(my_map)
    solver = CBS(parser._graph)
    result = solver.solve()

    if not result:
        return
    control = SimController(parser._graph, result)
    map_renderer = Map(parser._graph)
    agent_renderer = Agents(parser._graph)

    pygame.init()
    pygame.font.init()
    display = pygame.display.set_mode(map_renderer._screen)
    pygame.display.set_caption("FLY-IN")
    clock = pygame.time.Clock()

    running = True
    while running:
        # 1. event handling
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    control.advance_turn()
                if event.key == pygame.K_e:
                    control.jump_to_end()
            if event.type == pygame.QUIT:
                running = False
        # 2. get state
        if control.sim_complete:
            turn_state = control.final_state()
        else:
            turn_state = control.get_turn_state()
        turn_header = control.turn_header()

        # 3. draw from scratch
        display.fill("grey")
        map_renderer._draw_edges(display)
        map_renderer._draw_hubs(display)
        agent_renderer._turn_blits(display, turn_state)
        agent_renderer._turn_counter(display, turn_header)
        pygame.display.update()
        clock.tick(60)

    pygame.quit()
    for line in control.output:
        print(line)
    print(f"Total Cost: {result.total_cost}")
    print(f"Makespan: {result.makespan}")



if __name__ == "__main__":
    main()
