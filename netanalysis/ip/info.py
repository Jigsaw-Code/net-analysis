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

"""
Module to get information about an IP address.
"""

import argparse
import asyncio
import ipaddress
import pprint
import socket
import ssl
import sys
from typing import Dict, Any, Union

import certifi

import netanalysis.autonomous_system.simple_autonomous_system as sas
from netanalysis.autonomous_system import model

# Convenience type for any IP address.
IpAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


def resolve_ip(ip: IpAddress) -> str:
    """
    Does a reverse DNS lookup for the given IP address.

    Returns the domain from the PTR record.
    This is a convenience wrapper for socket.gethostbyaddr()
    """
    try:
        return socket.gethostbyaddr(ip.compressed)[0]
    except socket.herror:
        return None


_SSL_CONTEXT = ssl.create_default_context(
    purpose=ssl.Purpose.SERVER_AUTH, cafile=certifi.where())
_SSL_CONTEXT.check_hostname = False


async def get_tls_certificate(ip: Union[IpAddress, str],
                              server_hostname: str = None,
                              loop: asyncio.AbstractEventLoop = None,
                              timeout: float = 2.0) -> Dict[str, Any]:
    """
    Gets the TLS certificate for the given IP address and server hostname.

    This methods establishes a TCP connection to ip:443 and does a TLS handshake.
    If present, the server_hostname is sent as the TLS SNI.
    """
    ip = str(ip)
    if not loop:
        loop = asyncio.get_event_loop()
    transport, _proto = await asyncio.wait_for(loop.create_connection(
        asyncio.Protocol,
        host=ip,
        port=443,
        ssl=_SSL_CONTEXT,
        server_hostname=server_hostname), timeout)
    transport.close()
    return transport.get_extra_info("peercert")


def main(args):
    ip_address = args.ip_address
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
    try:
        cert = asyncio.get_event_loop().run_until_complete(
            get_tls_certificate(ip_address))
        if cert:
            print("TLS Certificate:\n%s" %
                  pprint.pformat(cert, width=100, compact=True))
    except Exception as e:
        print("TLS Certificate: %s" % repr(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gets information about the given IP address")
    parser.add_argument("ip_address", type=ipaddress.ip_address,
                        help="The IP address to get information for")
    sys.exit(main(parser.parse_args()))
