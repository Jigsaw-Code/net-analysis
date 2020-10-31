# Python environment set up

## Install Python 3 and pipenv

Install Python 3 if you don't have it already: https://www.python.org/downloads/

Install [Pipenv](https://docs.pipenv.org/) to manage Python environments and pip dependencies

```sh
python3 -m pip install pipenv
```

(You may need to source .bash_profile)

## Set up Pipenv Virtual Environment

Development should be done inside a Pipenv environment. Create and enter your Pipenv environment with:

```sh
PIPENV_VENV_IN_PROJECT=1 python3 -m pipenv install --dev
PIPENV_VENV_IN_PROJECT=1 python3 -m pipenv shell
```

`PIPENV_VENV_IN_PROJECT` will place the virtual environment in `./.venv/`.

On macOS you may get an error if you don't have the needed developer tools. You can use `xcode-select --install` to fix that.


### Add External Dependencies

Library dependencies must be listed in [setup.py](setup.py).

Dependencies for the development environment, such as development tools, should be listed in the [Pipfile](Pipfile).

After adding new dependencies, run `pipenv install` to refresh the environment.

## Test

Run the linter:
```
pylint
```

Run the type checker:
```
mypy
```

Run the unit tests:
```sh
python -m unittest -v
```
