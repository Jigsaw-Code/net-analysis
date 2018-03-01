load("@pip_packages//:requirements.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

py_binary(
    name = "fetch_measurements",
    srcs = ["fetch_measurements.py"],
    deps = [
        ":ooni_client",
        requirement("aiohttp"),
        # From https://aiohttp.readthedocs.io/en/stable/#library-installation:
        requirement("aiodns"),
        requirement("cchardet"),
        requirement("certifi"),
        requirement("iso3166"),
    ],
)


py_library(
    name = "ooni_client",
    srcs = ["ooni_client.py"],
    deps = [
        requirement("aiohttp"),
        # From https://aiohttp.readthedocs.io/en/stable/#library-installation:
        requirement("aiodns"),
        requirement("cchardet"),
        requirement("certifi"),
    ],
)

py_binary(
    name = "list_ooni_files",
    srcs = ["list_ooni_files.py"],
    deps = [
        requirement("boto3"),
    ],
)
