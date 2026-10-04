# Use an activated development environment.
install:
    python -m pip install -e '.[dev]'

test:
    python -m pytest tests/ -v

test-q:
    python -m pytest tests/ -q
