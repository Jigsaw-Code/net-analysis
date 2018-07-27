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

# pylint: disable=yield-inside-async-function

# Analysis ideas:
#
# - Ignore failed resolutions in control
#
# POSITIVE SIGNALS
# - Use HTTPS success
# - Create nested resolution whitelist with CNAMEs. Load from all files.
# - Load balancers are likely not censored results. Signs:
#   - ttl=0
#   - Multiple source domains
#
# NEGATIVE SIGNALS
# - Identify blackholes. Look at all data. Signs:
#   - Result AS is TRANSIT_ACCESS and in the client country
#   - Multiple source domains

import argparse
from collections import Counter, defaultdict
from enum import Enum
import glob
import ipaddress
import logging
import os.path
import random
import socket
import sys
from typing import Dict, List, Set
from urllib.parse import urlparse

import iso3166
import matplotlib.pyplot as pyplot
import networkx
import ujson as json

import netanalysis.analysis.simple_autonomous_system as sas
import netanalysis.model.autonomous_system as autonomous_system

class DnsResolution:
    def __init__(self, measurement, country=None, resolver_ip=None, client_as=None, time=None, url=None):
        self.measurement = measurement
        self.country = country or "ZZ"
        self.resolver_ip = resolver_ip
        self.client_as = client_as
        self.time = time
        self.cnames = []
        self.ips = []
        self.url = url  # For debugging

    def __repr__(self):
        return "DnsResolution(%s)" % repr(self.__dict__)


def path_get(d, path):
    roots = [d]
    for step in path:
        next_roots = []
        for root in roots:
            if type(root) != dict:
                break
            if step not in root:
                continue
            value = root[step]
            if type(value) == list:
                next_roots.extend(value)
            else:
                next_roots.append(value)
        roots = next_roots
    return roots


def get_dns_results(as_repo: autonomous_system.AsRepository,
                    measurements: List[Dict]) -> List[DnsResolution]:
    dns_results = []
    for m in measurements:
        time = m.get("measurement_start_time")
        country = m.get("probe_cc")
        url = urlparse(m.get("input"))
        client_asn = int(m.get("probe_asn")[2:])
        client_as = as_repo.get_as(client_asn)
        resolver_ip_str = path_get(m, ["test_keys", "client_resolver"])[0]
        resolver_ip = ipaddress.ip_address(resolver_ip_str) if resolver_ip_str else None
        for measurement in path_get(m, ["test_keys", "queries"]):
            dns_resolution = DnsResolution(m, country, resolver_ip, client_as, time, url)
            dns_resolution.cnames.append(measurement.get("hostname"))
            for answer in measurement.get("answers"):
                cname = answer.get("hostname")
                if cname:
                    dns_resolution.cnames.append(cname)
                else:
                    ip_str = answer.get("ipv4") or answer.get("ipv6")
                    if ip_str:
                        try:
                            dns_resolution.ips.append(ipaddress.ip_address(ip_str))
                        except ValueError:
                            logging.warning("Measurement %s: invalid IP answer %s", m["id"], ip_str)
            dns_results.append(dns_resolution)
    return dns_results


def get_control_resolutions(measurements):
    control_resolutions = []
    for m in measurements:
        resolution = DnsResolution(m, time=m.get("measurement_start_time"))
        resolution.cnames = [urlparse(m.get("input")).hostname]
        for ip_str in path_get(m, ["test_keys", "control", "dns", "addrs"]):
            try:
                resolution.ips.append(ipaddress.ip_address(ip_str))
            except ValueError:
                resolution.cnames.append(ip_str)
        if resolution.ips:
          control_resolutions.append(resolution)
    return control_resolutions


def count_resolutions(dns_results):
    edges = Counter()
    for resolution in dns_results:
        last_cname = resolution.cnames[0]
        for cname in resolution.cnames:
            edges[(last_cname, cname)] += 1
            last_cname = cname
        for ip_address in resolution.ips or ["<empty>"]:
            edges[(last_cname, ip_address)] += 1
    return edges


def get_ips(dns_resolutions):
    ips = set()
    for resolution in dns_resolutions:
        ips.update(resolution.ips)
    return ips


class DnsResolutionClassification(Enum):
    UNKNOWN = 0
    FREE = 1
    CENSORED = 2
    EMPTY = 3

def is_success_http_code(http_code):
    return 200 <= http_code and http_code <= 399

class DnsResolutionClassifier:
    def __init__(self) -> None:
        self._good_ips = set()  # type: Set
    
    def _get_ip_key(self, ip):
        return ipaddress.ip_network(ip).supernet(new_prefix=21)

    def add_good_resolution(self, resolution: DnsResolution):
        for ip in resolution.ips:
            self._good_ips.add(self._get_ip_key(ip))
    
    def classify_resolutions(self, resolutions: List[DnsResolution]):
        classifications = [DnsResolutionClassification.UNKNOWN] * len(resolutions)
        base_good_ips = 0
        while base_good_ips < len(self._good_ips):
            base_good_ips = len(self._good_ips)
            for ri, resolution in enumerate(resolutions):
                if classifications[ri] != DnsResolutionClassification.UNKNOWN:
                    continue
                if not resolution.ips:
                    classifications[ri] = DnsResolutionClassification.EMPTY
                    continue
                ip_keys = set(self._get_ip_key(ip) for ip in resolution.ips)
                for ip_key in ip_keys:
                    if ip_key in self._good_ips:
                        self._good_ips.update(ip_keys)
                        classifications[ri] = DnsResolutionClassification.FREE
                        break
                # If resolution is good, consider all ips good.
                if classifications[ri] == DnsResolutionClassification.FREE:
                    self._good_ips.update(ip_keys)
                    continue

                for ip in resolution.ips:
                    if not ip.is_global:
                        classifications[ri] = DnsResolutionClassification.CENSORED
                        break
        print("Good IPs: %s" % self._good_ips)
        return classifications

def group_by(sequence, get_key):
    result = defaultdict(list)
    for item in sequence:
        result[get_key(item)].append(item)
    return result

def make_resolver_key(as_repo, resolution):
    resolver_as = as_repo.get_as_for_ip(resolution.resolver_ip)
    if resolver_as == resolution.client_as:
        return "ISP"
    else:
        return resolver_as.org.name or resolver_as.org.id

def as_str(asys):
    org = asys.org.name or asys.org.id
    if org:
      return "%s (%s), Org: '%s' from %s" % (asys.name, asys.type.name, org[:20], asys.org.country)
    else:
      return asys.name


# Cache for ip -> hostname resolutions
_IP_NAMES = {}  # type: Dict[str, str]

def resolve_ip(ip):
    hostname = _IP_NAMES.get(ip.compressed, "")
    if hostname == "":
        try:
            hostname = socket.gethostbyaddr(ip.compressed)[0]
        except socket.herror:
            hostname = None
        _IP_NAMES[ip.compressed] = hostname
    return hostname

def show_resolutions_graph(as_repo, domain, control_resolutions, dns_resolutions):
    graph = networkx.DiGraph()
    cnames = set()
    ip_nets = set()
    ases = set()
    bad_edges = set()
    bad_nodes = set()
    good_edges = set()
    good_nodes = set()
    edge_countries = defaultdict(set)
    in_control = True
    for resolutions in [control_resolutions or [], dns_resolutions]:
        for resolution in resolutions:
            country = resolution.measurement["probe_cc"]
            last_cname = resolution.cnames[0]
            cnames.add(last_cname)
            for cname in resolution.cnames:
                edge = last_cname, cname
                graph.add_edge(*edge)
                edge_countries[edge].add(country)
                if in_control:
                    good_edges.add(edge)
                    good_nodes.add(cname)
                last_cname = cname
                cnames.add(cname)
            for ip_address in resolution.ips or [None]:
                if ip_address:
                    ip_net = ipaddress.ip_network(ip_address).supernet(new_prefix=22)
                    asys = as_repo.get_as_for_ip(ip_address)
                    as_str = asys.name or str(asys.id)
                    ases.add(as_str)
                    graph.add_edge(ip_net, as_str)
                    if not ip_address.is_global:
                        bad_edges.add((last_cname, ip_net))
                        bad_nodes.add(ip_net)
                else:
                    ip_net = "<empty>"
                ip_nets.add(ip_net)
                edge = last_cname, ip_net
                graph.add_edge(*edge)
                edge_countries[edge].add(country)
                if in_control:
                    good_edges.add(edge)
                    good_nodes.add(ip_net)
        in_control = False

    nodes_pos = networkx.spring_layout(graph)
    min_x = min(x for x, _ in nodes_pos.values())
    max_x = max(x for x, _ in nodes_pos.values())
    range_x = max_x - min_x
    for node, pos in list(nodes_pos.items()):
        if isinstance(node, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
            nodes_pos[node] = (min_x + range_x * 0.5 + (pos[0] - min_x) * 0.3, pos[1])
        else:
            nodes_pos[node] = (min_x + range_x * 0.1 + (pos[0] - min_x) * 0.3, pos[1])
    nodes_pos[domain] = (min_x, nodes_pos[domain][1])
    for asys in ases:
        nodes_pos[asys] = (max_x, nodes_pos[asys][1])
    networkx.draw_networkx_nodes(graph, nodelist=cnames, pos=nodes_pos, node_color="b")
    networkx.draw_networkx_nodes(graph, nodelist=ip_nets - bad_nodes, pos=nodes_pos, node_color="gray")
    networkx.draw_networkx_labels(graph, pos=nodes_pos, font_size=8)
    networkx.draw_networkx_edges(graph, pos=nodes_pos, alpha=0.25)
    edge_labels = dict((key, " ".join(countries) if len(countries) <= 3 else "*") for key, countries in edge_countries.items())
    networkx.draw_networkx_edge_labels(graph, edge_labels=edge_labels, pos=nodes_pos, alpha=0.5, font_size=8, label_pos=0.2)
    networkx.draw_networkx_edges(graph, edgelist=good_edges, pos=nodes_pos, alpha=0.5, edge_color="g")
    networkx.draw_networkx_nodes(graph, nodelist=good_nodes, pos=nodes_pos, node_color="g")
    networkx.draw_networkx_edges(graph, edgelist=bad_edges, pos=nodes_pos, alpha=0.5, edge_color="r")
    networkx.draw_networkx_nodes(graph, nodelist=bad_nodes, pos=nodes_pos, node_color="r")
    pyplot.show()


def main(args):
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    measurements = []
    for filename in glob.iglob(os.path.join(args.measurements_dir, args.domain, "*", "*")):
        with open(filename) as file:
            measurements.append(json.load(file))

    as_repo = sas.create_default_as_repo()

    classifier = DnsResolutionClassifier()
    control_resolutions = get_control_resolutions(measurements)
    for resolution in control_resolutions:
        classifier.add_good_resolution(resolution)

    print("\nCONTROL")
    for resolution, count in count_resolutions(control_resolutions).most_common():
        print("%s -> %s: %d" % (resolution[0], resolution[1], count))

    dns_resolutions = get_dns_results(as_repo, measurements)
    show_resolutions_graph(as_repo, args.domain, control_resolutions, dns_resolutions)

    print("\nTESTS")
    classified_resolutions = zip(dns_resolutions,
                                 classifier.classify_resolutions(dns_resolutions))

    for country_code, country_classifications in group_by(classified_resolutions, lambda e: e[0].country).items():
        try:
            country_name = iso3166.countries.get(country_code).name
        except KeyError:
            country_name = "Unknown"
        print("\n=============\n= %s (%s)\n=============" % (country_name, country_code))
        country_count = len(country_classifications)
        grouped_country_classifications = group_by(country_classifications, lambda e: e[1])
        for classification, entries in grouped_country_classifications.items():
            class_count = len(entries)
            prefix = "All " if class_count == country_count else ""
            print(" %s%s: %d/%d" % (prefix, classification.name.lower(), class_count, country_count))
        #if len(grouped_country_classifications[DnsResolutionClassification.FREE]) == country_count:
        #    continue

        print("\n By Resolver:")
        for resolver_key, resolver_classifications in group_by(country_classifications,
                                                      lambda e: make_resolver_key(as_repo, e[0])).items():
            print("  - %s:" % resolver_key)
            resolver_count = len(resolver_classifications)
            for classification, entries in group_by(resolver_classifications, lambda e: e[1]).items():
                class_count = len(entries)
                prefix = "All " if class_count == resolver_count else ""
                print("      %s%s: %d/%d" % (prefix, classification.name.lower(), class_count, resolver_count))

        for classification, entries in grouped_country_classifications.items():
            if classification == DnsResolutionClassification.EMPTY or not entries: continue
            print("\n %s resolutions:" % classification.name)
            displayed = set()
            for resolution, _ in entries:
                display_str = ",\n     ".join(["%s (%s)" % (resolve_ip(ip) or ip, as_str(as_repo.get_as_for_ip(ip))) for ip in sorted(resolution.ips)])
                if display_str in displayed:
                    continue
                print("  - [%s] %s\n     => %s" % (display_str, resolution.url.geturl(),
                      path_get(resolution.measurement, ["test_keys", "requests", "failure"])))
                displayed.add(display_str)
                # print(json.dumps(resolution.measurement, indent=4, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Analyze DNS measurements from OONI")
    parser.add_argument("--measurements_dir", type=str, required=True)
    parser.add_argument("--domain", type=str, required=True)
    parser.add_argument("--debug", action="store_true")
    sys.exit(main(parser.parse_args()))
