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

import ipaddress
import os.path


class Server:  # pylint: disable=too-few-public-methods
    def __init__(self, ip_address, location_id: str) -> None:
        self.ip_address = ip_address
        self.location_id = location_id


class GoogleDns:
    def __init__(self):
        self.networks = []

    def add_network(self, ip_network, location_id):
        self.networks.append((ip_network, location_id))

    def get_server(self, ip_address):
        for ip_network, location_id in self.networks:
            if ip_address in ip_network:
                return Server(ip_address, location_id)
        return None


def create_google_dns_from_filename(filename):
    google_dns = GoogleDns()
    with open(filename) as data_file:
        for line in data_file:
            ip_address_str, location_id = line.strip().split()
            ip_network = ipaddress.ip_network(ip_address_str)
            google_dns.add_network(ip_network, location_id)
    return google_dns


def create_default_google_dns():
    filename = os.path.join(os.path.dirname(__file__),
                            "google_dns_locations.txt")
    return create_google_dns_from_filename(filename)
