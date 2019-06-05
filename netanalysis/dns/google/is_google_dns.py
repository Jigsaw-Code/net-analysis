#!/usr/bin/python
#
# Copyright 2017 Jigsaw Operations LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import ipaddress
import sys

import netanalysis.google.google_dns as gd


def main(args):
    ip_address = args.ip_address[0]
    google_dns = gd.create_default_google_dns()
    server = google_dns.get_server(ip_address)
    if not server:
        print("%s is NOT a Google DNS server" % ip_address)
        return 1
    print("%s is a Google DNS server at %s" % (ip_address, server.location_id))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Checks if the given ip address is a Google DNS one')
    parser.add_argument('ip_address', type=ipaddress.ip_address,
                        nargs=1, help='The IP address to check')
    sys.exit(main(parser.parse_args()))
