SCRIPT := fly_in
ARGS ?= maps/easy/01_linear_path.txt

.PHONY: all install run debug clean fclean lint lint-strict

install: check-uv
	uv sync

check-uv: 
	@command -v uv >/dev/null 2>&1 || ( \
		echo "uv not found, installing ..." && \
		curl -LsSf https://astral.sh/uv/install.sh | sh \
		)

all: install run

run:
	uv run -m $(SCRIPT) $(ARGS)

debug:
	uv run -m pdb $(SCRIPT) $(ARGS)

clean:
	@echo "Cleaning caches and temporary files..."
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

fclean: clean
	find . -type d -name ".venv" -exec rm -rf {} +

lint:
	@echo "Checking flake8 ..."
	flake8 .
	@echo "Checking mypy ..."
	uv run mypy .