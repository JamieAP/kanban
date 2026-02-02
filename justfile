# Kanban CLI

# Update user installation
install:
    ~/.local/share/kanban/venv/bin/pip install -q .
    @echo "Updated kanban at ~/.local/bin/kanban"

# Run tests
test:
    ~/.local/share/kanban/venv/bin/pytest tests/ -v

# Run tests quietly
test-q:
    ~/.local/share/kanban/venv/bin/pytest tests/ -q
