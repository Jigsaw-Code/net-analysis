#!/usr/bin/python
#
# Copyright 2018 Jigsaw Operations LLC
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
import asyncio
import ipaddress
import pprint
import socket
import sys

import netanalysis.autonomous_system.simple_autonomous_system as sas
from netanalysis.autonomous_system import model
from netanalysis.dns import domain_ip_validator


def resolve_ip(ip) -> str:
    try:
        return socket.gethostbyaddr(ip.compressed)[0]
    except socket.herror:
        return None


def main(args):
    ip_address = args.ip_address[0]
    as_repo = sas.create_default_as_repo()  # type: model.AsRepository
    asys = as_repo.get_as_for_ip(ip_address)  # type: model.AutonomousSytem
    print("ASN:  %d (%s)" % (asys.number, asys.name))
    # AS Type is is experimental and outdated data.
    print("Type: %s" % asys.type.name)
    print("Org:  %s (country: %s, name: %s)" %
          (asys.org.id, asys.org.country, asys.org.name))
    if ip_address.is_global:
        hostname = resolve_ip(ip_address)
        if hostname:
            print("Hostname: %s" % hostname)
    else:
        print("IP in not global")
    validator = domain_ip_validator.DomainIpValidator()
    try:
        cert = asyncio.get_event_loop().run_until_complete(
            validator.get_cert(None, ip_address))
        if cert:
            print("TLS Certificate:\n%s" %
                  pprint.pformat(cert, width=100, compact=True))
    except Exception as e:
        print("TLS Certificate: %s" % repr(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Gets information about the given IP address')
    parser.add_argument('ip_address', type=ipaddress.ip_address,
                        nargs=1, help='The IP address to get information fo')
    sys.exit(main(parser.parse_args()))
