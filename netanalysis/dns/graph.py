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

from collections import defaultdict
import ipaddress
import logging
import os

from matplotlib import pyplot
import networkx as nx
import ujson as json

import netanalysis.dns.serialization as ds


def _get_edge_target(data):
    if hasattr(data, "cname"):
        return data.cname.lower()
    if hasattr(data, "ip"):
        net = ipaddress.ip_network(data.ip).supernet(new_prefix=24)
        return net.compressed


def load_dns_records_graph(dns_measurements_filename: str,
                           update_progress=lambda done, total: None) -> nx.MultiDiGraph:  
    graph = nx.MultiDiGraph()
    file_size = os.stat(dns_measurements_filename).st_size
    update_progress(0, file_size)
    done_bytes = 0
    done_step = 0
    with open(dns_measurements_filename) as measurements_file:
        for line in measurements_file:
            try:
                measurement = ds.measurement_from_json(json.loads(line))
                for record in measurement.records:
                    source = record.name.lower()
                    target = _get_edge_target(record.data)
                    if not target:
                        raise ValueError("No record target for DnsMeasurement: %s" % measurement)
                    graph.add_edge(source, target, None, record=record, measurement=measurement)
            except Exception as e:
                logging.error("Failed to process measurement:\n%s", line)
                raise e
            done_bytes += len(line)
            new_step = int(done_bytes * 100 / file_size / 5)
            if new_step != done_step:
                update_progress(done_bytes, file_size)
            done_step = new_step
    return graph


def domain_view(multi_graph: nx.MultiDiGraph, root_domain: str) -> nx.MultiDiGraph:
    """Returns the subgraph rooted at the given domain."""
    return multi_graph.subgraph(nx.dfs_preorder_nodes(multi_graph, root_domain))


def country_view(multi_graph: nx.MultiDiGraph, client_country: str) -> nx.MultiDiGraph:
    """Returns a view of the edges restricted to the given client country."""
    country_edges = [(u, v, k) for u, v, k, measurement in multi_graph.edges(
        keys=True, data="measurement") if measurement.client_country == client_country]
    return multi_graph.edge_subgraph(country_edges)

