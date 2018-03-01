load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository")

###########################################################
# Python
# From https://github.com/bazelbuild/rules_python

git_repository(
    name = "io_bazel_rules_python",
    remote = "https://github.com/bazelbuild/rules_python.git",
    commit = "73a154a181a53ee9e021668918f8a5bfacbf3b43",  
)

load("@io_bazel_rules_python//python:pip.bzl", "pip_repositories", "pip_import")
pip_repositories()

pip_import(
    name = "pip_packages",
    requirements = "//third_party:py_requirements.txt",
)
load("@pip_packages//:requirements.bzl", "pip_install")
pip_install()
