import argparse


class CLIParser():
    """Configure and parse the command-line map argument."""

    def __init__(self) -> None:
        """Create the parser and parse the process arguments.

        Returns:
            None.
        """
        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            description="Drone Routing CLI")
        self._configure()
        self.args: argparse.Namespace = self._parse()

    def _configure(self) -> None:
        """Register the positional input-map argument.

        Returns:
            None.
        """
        self.parser.add_argument("input_map",
                                 type=str,
                                 help="Relative path to puzzle map")

        self.parser.add_argument("-v", "--verbose",
                                 action="store_true",
                                 help="Print detailed simulation metadata")

        self.parser.add_argument("-c", "--cost-per-agent",
                                 action="store_true",
                                 help="Print cost per agent")

        self.parser.add_argument("-cp", "--capacity-info",
                                 action="store_true",
                                 help="Print cap info")
        return None

    def _parse(self) -> argparse.Namespace:
        """Parse command-line arguments.

        Returns:
            Parsed command-line arguments.
        """
        return self.parser.parse_args()
