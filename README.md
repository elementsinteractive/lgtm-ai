<p align="center">
  <img alt="lgtm-logo" width="150" src="./assets/lgtm-large.png">
</p>

# lgtm

[![💀 - Made with Skeleton](https://img.shields.io/badge/💀-Made_with_Skeleton-0e7fbf)](https://gitlab.com/namespace/elements/backend/pypackage-skeleton)
![Python Version](https://img.shields.io/badge/python-3.12%20|%203.13-blue?logo=python&logoColor=yellow)
[![pipeline status](https://gitlab.com/namespace/elements/backend/lgtm/badges/main/pipeline.svg)](https://gitlab.com/namespace/elements/backend/lgtm/-/commits/main)
[![coverage report](https://gitlab.com/namespace/elements/backend/lgtm/badges/main/coverage.svg)](https://gitlab.com/namespace/elements/backend/lgtm/-/commits/main)
[![Latest Release](https://gitlab.com/namespace/elements/backend/lgtm/-/badges/release.svg)](https://gitlab.com/namespace/elements/backend/lgtm/-/releases)


**Documentation:** https://namespace.gitlab.io/elements/backend/lgtm

---

Your AI-powered code review companion


**Table of Contents**
- [Installation](#installation)
- [Running the project](#running-the-project)
- [Managing requirements](#managing-requirements)
- [Contributing](#contributing)
  - [API Development Guidelines](#api-development-guidelines)
  - [Code Review Guidelines](#code-review-guidelines)

## Installation

To install this package, you need a [personal access token](https://gitlab.com/-/profile/personal_access_tokens). 


```sh
# through the project repository
pip install lgtm --index-url https://__token__:<your_personal_token>@gitlab.com/api/v4/projects/<PROJECT-ID>/packages/pypi/simple

# through a group repository
pip install lgtm --index-url https://__token__:<your_personal_token>@gitlab.com/api/v4/groups/<GROUP-ID>/-/packages/pypi/simple
```

You can also configure `pip` globally in your `.pypirc` file:

```
[gitlab]
repository = https://gitlab.com/api/v4/projects/<PROJECT-ID>/packages/pypi
username = __token__
password = <your personal access token>
```

For a comprehensive guide of how to set this up, and to make it work with `poetry` and/or `docker`, take a look at [this guide](https://www.notion.so/msdevelopment/How-to-use-Gitlab-s-registry-for-PyPi-d9f8fdbc00144dc786de550153c56cd9?pvs=4).


## Running the project
This project uses [`just`](https://github.com/casey/just) recipes to do all the basic operations (testing the package, formatting the code, etc.).

Installation: 

```sh
brew install just
# or
snap install --edge --classic just
```

It requires [poetry](https://python-poetry.org/docs/#installation).

These are the available commands for the justfile:

```
Available recipes:
    help                        # Shows list of recipes.
    venv                        # Generate the virtual environment.
    clean                       # Cleans all artifacts generated while running this project, including the virtualenv.
    test *test-args=''          # Runs the tests with the specified arguments (any path or pytest argument).
    t *test-args=''             # alias for `test`
    test-all                    # Runs all tests including coverage report.
    format                      # Format all code in the project.
    lint                        # Lint all code in the project.
    docs                        # Serve the documentation in a local server.
    pre-commit *precommit-args  # Runs pre-commit with the given arguments (defaults to install).
    spellcheck *codespell-args  # Spellchecks your markdown files.
    lint-commit                 # Lints commit messages according to conventional commit rules.
```

To run the tests of this package, simply run:

```sh
# All tests
just t

# A single test
just t tests/test_dummy.py

# Pass arguments to pytest like this
just t -k test_dummy -vv
```

## Managing requirements

`poetry` is the tool we use for managing requirements in this project. The generated virtual environment is kept within the directory of the project (in a directory named `.venv`), thanks to the option `POETRY_VIRTUALENVS_IN_PROJECT=1`. Refer to the [poetry documentation](https://python-poetry.org/docs/cli/) to see the list of available commands.

As a short summary:

- Add a dependency:

        poetry add foo-bar

- Remove a dependency:

        poetry remove foo-bar

- Update a dependency (within constraints set in `pyproject.toml`):

        poetry update foo-bar

- Update the lockfile with the contents of `pyproject.toml` (for instance, when getting a conflict after a rebase):

        poetry lock

- Check if `pyproject.toml` is in sync with `poetry.lock`:

        poetry lock --check


## Contributing
In this project we enforce [conventional commits](https://www.conventionalcommits.org) guidelines for commit messages. The usage of [commitizen](https://commitizen-tools.github.io/commitizen/) is recommended, but not required. Story numbers (JIRA, etc.) must go in the scope section of the commit message. Example message:

```
feat(JIRA-XXX): add new feature x
```

Merge requests must be approved before they can be merged to the `main` branch, and all the steps in the `ci` pipeline must pass.

This project includes an optional pre-commit configuration. Note that all necessary checks are always executed in the ci pipeline, but
configuring pre-commit to execute some of them can be beneficial to reduce late errors. To do so, simply execute the following just recipe:

```
just pre-commit
```

## Evaluating lgtm (WIP)

If you are working on improving the prompts of the AI, the models, or other areas of lgtm that might affect the quality of the reviews,
this repo comes with a script that will help you bootstrap your evaluations.

In your branch, run the following command:

```sh
python scripts/evaluate_review_quality.py --git-api-key $GITLAB_TOKEN --ai-api-key $OPENAI_API_KEY
```

That will create several markdown files with the results of several reviews done with the changes in your branch.

You can use these reviews to evaluate the quality of them, and whether your changes are improving lgtm!

Be sure to include the results of the assessment in your PR, because that will help reviewers see your improvements.

### [API Development Guidelines](https://www.notion.so/msdevelopment/Development-Guidelines-623677e75f69473abc743ce1d381eb6b)
### [Code Review Guidelines](https://www.notion.so/msdevelopment/Code-Review-Guidelines-82023d1814b442e486ed38e648c5d86e)
