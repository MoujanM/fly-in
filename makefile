# SCRIPT := a_maze_ing.py
# CONFIG ?= config.txt


.PHONY: install run debug clean-venv clean lint lint-strict

install: check-uv
	uv sync

check-uv: 
	@command -v uv >/dev/null 2>&1 || ( \
		echo "uv not found, installing ..." && \
		curl -LsSf https://astral.sh/uv/install.sh | sh \
		)


# $(VENV)/bin/activate:
# 	python3 -m venv $(VENV)
# 	$(PIP) install --upgrade pip

# # all: $(INSTALLED)

# install: $(VENV)/bin/activate
# 	$(PIP) install -r $(REQ)

# run:
# 	$(PYTHON) $(SCRIPT) $(CONFIG)

# debug:
# 	$(PYTHON) -m pdb $(SCRIPT) $(CONFIG)

clean:
	@echo "Cleaning caches and temporary files..."
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-venv: clean
	@echo "Removing virtual env directory"
	rm -rf .venv

lint:
	@echo "Checking flake8 ..."
	flake8 src/ visualizer/ main.py controller.py
	@echo "Checking mypy ..."
	$(VENV)/bin/mypy utils/ mazegen/ $(SCRIPT) --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs