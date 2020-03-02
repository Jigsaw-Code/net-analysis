# Python environment set up

## Install Python 3.6 and pipenv

Install Python3: https://www.python.org/downloads/

Install [pipenv](https://docs.pipenv.org/) to manage Python environments and pip dependencies

```sh
pip3 install pipenv
```

(You may need to source .bash_profile)

## Set up Workspace Virtual Environment

Run

```sh
`PIPENV_VENV_IN_PROJECT=1 pipenv install
```

That will create a Python 3.6 virtual environment under `.venv` to be used by Bazel, and install the development tools (`pylint`, `mypy`, `autopep8`, `rope`)

On macOS you may get an error if you don't have the needed developer tools. You can use `xcode-select --install` to fix that.

## Add External Dependencies

Libraries used in code should be listed in [setup.py](setup.py).

Tools for development should be listed in the [Pipfile](Pipfile).

After adding new dependencies to the files, run `pipenv install` to refresh the environment.