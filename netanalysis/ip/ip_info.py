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

# TODO: 
# - Get SOA for PTR record
# - Show city and country
# - Refactor into IpInfoService

import abc
import argparse
import asyncio
import ipaddress
import pprint
import socket
import sys

import geoip2.database

from netanalysis.dns import domain_ip_validator
from netanalysis.infrastructure.resources import resource_filename

from . import model
from . import simple_autonomous_system as sas


class IpInfoService:
    def __init__(self, as_repo: model.AsRepository, geoip2_asn, geoip2_country):
        self._as_repo = as_repo
        self._geoip2_asn = geoip2_asn
        self._geoip2_country = geoip2_country
    
    def get_as(self, ip: model.IpAddress) -> model.AutonomousSystem:
        try:
            asn = self._geoip2_asn.asn(ip.compressed).autonomous_system_number
        except:
            asn = -1
        return self._as_repo.get_as(asn)
    
    def get_country(self, ip: model.IpAddress) -> (str, str):
        "Returns country code and country name for the IP"
        # TODO: Consider exposing the confidence value
        try:
            country_record = self._geoip2_country.country(
                ip.compressed).country  # type: geoip2.records.Country
            if not country_record:
                return ("ZZ", "Unknown")
            return (str(country_record.iso_code), str(country_record.name))
        except:
            return ("ZZ", "Unknown")

    def resolve_ip(self, ip: model.IpAddress) -> str:
        try:
            return socket.gethostbyaddr(ip.compressed)[0]
        except socket.herror:
            return None        


def create_default_ip_info_service() -> IpInfoService:
    as_repo = sas.create_default_as_repo()
    ip_asn = geoip2.database.Reader(resource_filename(
        "third_party/maxmind/GeoLite2-ASN/GeoLite2-ASN.mmdb"))
    ip_country = geoip2.database.Reader(resource_filename(
        "third_party/maxmind/GeoLite2-Country/GeoLite2-Country.mmdb"))
    return IpInfoService(as_repo, ip_asn, ip_country)


def main(args):
    ip_info = create_default_ip_info_service()
    
    ip_address = args.ip_address[0]
    print("Country:  %s (%s)" % ip_info.get_country(ip_address))
    asys = ip_info.get_as(ip_address)  # type: model.AutonomousSytem
    print("ASN:  %d (%s)" % (asys.id, asys.name))
    # AS Type is is experimental and outdated data.
    print("Type: %s" % asys.type.name)
    print("Org:  %s (country: %s, name: %s)" % (asys.org.id, asys.org.country, asys.org.name))
    if ip_address.is_global:
        hostname = ip_info.resolve_ip(ip_address)
        if hostname:
            print("Hostname: %s" % hostname)
    else:
        print("IP in not global")
    validator = domain_ip_validator.DomainIpValidator()
    try:
        cert = asyncio.get_event_loop().run_until_complete(validator.get_cert(None, ip_address))
        if cert:
            print("TLS Certificate:\n%s" % pprint.pformat(cert, width=100, compact=True))
    except Exception as e:
        print("TLS Certificate: %s" % repr(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Gets information about the given IP address')
    parser.add_argument('ip_address', type=ipaddress.ip_address,
                        nargs=1, help='The IP address to get information fo')
    sys.exit(main(parser.parse_args()))
