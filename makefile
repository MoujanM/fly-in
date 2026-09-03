SCRIPT := fly_in

.PHONY: all install run debug clean lint lint-strict

install: check-uv
	uv sync

check-uv: 
	@command -v uv >/dev/null 2>&1 || ( \
		echo "uv not found, installing ..." && \
		curl -LsSf https://astral.sh/uv/install.sh | sh \
		)

all: install 
	run

run:
	uv run -m $(SCRIPT)

debug:
	uv run -m pdb $(SCRIPT)

clean:
	@echo "Cleaning caches and temporary files..."
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

lint:
	@echo "Checking flake8 ..."
	flake8 .
	@echo "Checking mypy ..."
	uv run mypy .