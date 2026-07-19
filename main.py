from src.parser import Parser
from src.cbs import CBS
from src.models import CBSResult


def main():
    map_files = ["./maps/easy/01_linear_path.txt",
                 "./maps/easy/02_simple_fork.txt",
                 "./maps/easy/03_basic_capacity.txt"
    ]

    for i, m in enumerate(map_files):
        print(f"Map {i}")
        parser = Parser(m)
        solver = CBS(parser._graph)
        cbs_res = solver.solve()
        simulation = solver.get_turn_desc(cbs_res)
        for turn in simulation:
            print(turn)
        print("\n")





if __name__ == "__main__":
    main()
