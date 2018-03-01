# Python environment set up

## Install Python 3.6 and pipenv

Install Python3: https://www.python.org/downloads/

Install [pipenv](https://docs.pipenv.org/) to manage Python environments and pip dependencies:
```
pip3 install pipenv
```
(You may need to source .bash_profile)


## Set up Workspace Virtual Environment

Run

````
./setup_python.sh
````

That will create a Python 3.6 virtual environment under `.venv` to be used by Bazel, and install the development tools (`pylint`, `mypy`, `autopep8`, `rope`)

On macOS you may get an error if you don't have the needed developer tools. You can use `xcode-select --install` to fix that.

## Add External Dependencies

Libraries used in code should be listed in [third_party/py_requirements.txt](third_party/py_requirements.txt).

Tools for development should be listed in [py_dev_requirements.txt](py_dev_requirements.txt).

To install the new dependencies without re-creating the Python virtual environment, run

```
./pipenv.sh install -r py_dev_requirements.txt
```