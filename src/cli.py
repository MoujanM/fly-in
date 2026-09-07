import argparse


class CLIParser():
    def __init__(self) -> None:
        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            description="Drone Routing CLI")
        self._configure()
        self.args: argparse.Namespace = self._parse()

    def _configure(self) -> None:
        self.parser.add_argument("input_map",
                                 type=str,
                                 help="Relative path to puzzle map")
        return None

    def _parse(self) -> argparse.Namespace:
        return self.parser.parse_args()
