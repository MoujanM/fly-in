# VENV := maze_env
# PYTHON := $(VENV)/bin/python
# PIP := $(VENV)/bin/pip
# REQ := utils/requirements.txt
# SCRIPT := a_maze_ing.py
# CONFIG ?= config.txt
# # VENVDONE := $(VENV)/.venv_created
# #INSTALLED := $(VENV)/.requirements_installed

# .PHONY: install run debug clean-venv clean lint

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

# clean:
# 	@echo "Cleaning caches and temporary files..."
# 	rm -rf .mypy_cache
# 	find . -type d -name "__pycache__" -exec rm -rf {} +
# 	find . -type f -name "*.pyc" -delete

# clean-venv: clean
# 	@echo "Removing virtual env directory"
# 	rm -rf $(VENV)

# lint:
# 	@echo "Checking flake8 ..."
# 	$(VENV)/bin/flake8 utils/ mazegen/ $(SCRIPT)
# 	@echo "Checking mypy ..."
# 	$(VENV)/bin/mypy utils/ mazegen/ $(SCRIPT) --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs