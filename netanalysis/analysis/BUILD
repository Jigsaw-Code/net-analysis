load("@pip_packages//:requirements.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

py_binary(
  name = "analyze_domain",
  srcs = ["analyze_domain.py"],
  deps = [
    ":simple_autonomous_system",
    requirement("iso3166"),
    requirement("matplotlib"),
    requirement("networkx"),
    requirement("pydot"),
  ],
)

py_binary(
  name = "ip_info",
  srcs = ["ip_info.py"],
  deps = [
    ":simple_autonomous_system",
  ],
)

py_library(
  name = "simple_autonomous_system",
  srcs = ["simple_autonomous_system.py"],
  deps = [
    "//netanalysis/model:autonomous_system",
    "//netanalysis/infrastructure:resources",
    requirement("geoip2"),
  ],
  data = [
    "//third_party/caida.org:as_data",
    "//third_party/maxmind:ip_asn_data",
  ],
)

py_test(
  name = "simple_autonomous_system_test",
  srcs = ["simple_autonomous_system_test.py"],
  data = [
    ":simple_autonomous_system",
  ],
  size = "small",
)
