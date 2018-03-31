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

import asyncio
import ipaddress
import os.path

from IPython.display import display
import ipywidgets as widgets
from matplotlib import pyplot

from netanalysis.dns import classifier as dc
from netanalysis.dns import graph as dg
from netanalysis.dns import domain_ip_validator


class AnalysisApp:
    def __init__(self, measurements_dir: str) -> None:
        self.progress_bar = widgets.IntProgress(
            value=0,
            step=1,
            description='Loading',
            orientation='horizontal'
        )
        display(self.progress_bar)
        self.dns_graph = dg.load_dns_records_graph(
            os.path.join(measurements_dir, "dns_records.json"),
            self.update_progress)
        self.progress_bar.bar_style = "success"

    def domain_app(self, domain):
        return DomainApp(self.dns_graph, domain)

    def update_progress(self, done, total):
        self.progress_bar.max = total
        self.progress_bar.value = done


def _truncate(text: str, max_len: int) -> str:
    """Truncates the text to the given length.

    Adds a trailing elipsis if text gets truncated.
    """
    if len(text) > max_len:
        return text[:max_len - 1] + "…"
    return text


class DomainApp:
    def __init__(self, dns_graph, domain):
        self.domain = domain
        self.domain_graph = dg.domain_view(dns_graph, self.domain)
        self.classifier = dc.EdgeClassifier(self.domain_graph)

    def display_graph(self, country=None):
        pyplot.figure(tight_layout=dict(pad=0))
        pyplot.axis("off")
        domain_graph = self.domain_graph
        if country:
            domain_graph = dg.country_view(domain_graph, country)
        dc.draw_graph(self.classifier.class_graph.edge_subgraph(
            domain_graph.edges()))
        pyplot.show()

    def get_ips(self, net):
        ips = set()
        for _, _, record in self.domain_graph.in_edges(net, data="record"):
            if hasattr(record.data, "ip"):
                ips.add(str(record.data.ip))
        return ips

    async def tls_verify_unknowns(self):
        validator = domain_ip_validator.DomainIpValidator()
        # Try short domains first: they usually validate CNAMES, which tend to be longer.
        for domain, target in sorted(self.classifier.class_graph.edges(), key=lambda e: (len(e[0]), e[1])):
            if self.classifier.get_class(domain, target) != dc.EdgeClass.UNKNOWN:
                continue
            try:
                ipaddress.ip_network(target)
            except (ipaddress.AddressValueError, ValueError):
                continue
            net = target
            print("Checking IPs for {} - {}".format(domain, net))
            for ip in list(self.get_ips(net))[:2]:
                print("    Validating {}: ".format(ip), end="")
                try:
                    await validator.validate_ip(domain, ip)
                    print("VALID")
                    self.classifier.add_good_edge(
                        domain, net, "Pass TLS validation")
                    break
                except Exception as e:
                    print(_truncate(repr(e), 200))
