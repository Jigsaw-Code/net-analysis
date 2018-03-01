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

You must do all development inside the Virtual Environment. Load the environment with:

```
./pipenv.sh shell
```

This will start a shell where `python` is the interpreter from the virtual environment.
Unfortunately this is needed because the `pip_import` rules hard-code `python` as the interpreter. See [Fetching dependencies assumer python2](https://github.com/google/containerregistry/issues/42).


## Add PIP Dependencies

We use [`pip_import`](https://github.com/bazelbuild/rules_python/blob/master/docs/python/pip.md#pip_import) to pull pip dependencies.

To add a new pip dependency:

1. Add it to [`third_party/py_requirements.txt`](third_party/py_requirements.txt).

1. Depend on it in your Python target:

````
load("@pip_packages//:requirements.bzl", "requirement")

py_library(
    name = "bar",
    ...
    deps = [
       "//my/other:dep",
       requirement("futures"),
       requirement("mock"),
    ],
)
````


## Add Development Tools

Add new development tools to `py_dev_requirements.txt` and rerun `./setup_python.sh`.
