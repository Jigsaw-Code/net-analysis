py_library(
  name = "google_dns",
  srcs = ["google_dns.py"],
  data = ["google_dns_locations.txt"],
)

py_test(
  name = "google_dns_test",
  srcs = ["google_dns_test.py"],
  deps = [
    ":google_dns",
  ],
  size = "small",
)

py_binary(
  name = "is_google_dns",
  srcs = ["is_google_dns.py"],
  data = [":google_dns"],
)
