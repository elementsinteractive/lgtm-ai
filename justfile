
# VARIABLE DEFINITIONS
venv := ".venv"
bin := venv + "/bin"
python_version := "python3.13"
run := "poetry run"
target_dirs := "src tests"

# SENTINELS
venv-exists := path_exists(venv)

# RECIPES

# Shows list of recipes.
help:
    just --list --unsorted

# Generate the virtual environment.
venv:
    @if ! {{ venv-exists }}; \
    then \
    POETRY_VIRTUALENVS_IN_PROJECT=1 poetry env use {{ python_version }}; \
    poetry install; \
    fi

# Cleans all artifacts generated while running this project, including the virtualenv.
clean:
    @rm -f .coverage*
    @rm -rf {{ venv }}

alias t := test
# Runs the tests with the specified arguments (any path or pytest argument).
test *test-args='': venv
    {{ run }} pytest {{ test-args }} --no-cov

# Runs all tests including coverage report.
test-all: venv
    {{ run }} pytest

# Format all code in the project.
format *files=target_dirs: venv
    {{ run }} ruff check {{ files }} --fix
    {{ run }} ruff format {{ files }}

# Lint all code in the project.
lint report="false": venv
    {{ run }} ruff format --check {{ target_dirs }}
    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--output-format gitlab > tests/gl-code-quality-report.json" } else { "" } }}
    {{ run }} mypy {{ target_dirs }}

# Serve the documentation in a local server.
docs: venv
    {{ run }} mkdocs serve

# Runs pre-commit with the given arguments (defaults to install).
pre-commit *precommit-args="install": venv
    {{ run }} pre-commit {{ precommit-args }}

# Spellchecks your markdown files.
spellcheck *codespell-args: venv
    {{ run }} codespell {{ codespell-args }} **/*.md

# Lints commit messages according to conventional commit rules.
lint-commit: venv
    {{ run }} cz check --rev-range main..HEAD


