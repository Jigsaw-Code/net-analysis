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

from collections import deque, namedtuple
from enum import Enum
from itertools import chain
from typing import Set

import networkx as nx
from numpy.random import RandomState

class EdgeClass(Enum):
    UNKNOWN = 0
    GOOD = 1
    BAD = 2


Evaluation = namedtuple("Evaluation", ["classification", "reason"])


def edge_class(class_graph: nx.DiGraph, u: str, v: str) -> EdgeClass:
    try:
        return class_graph[u][v]["eval"].classification
    except KeyError:
        return EdgeClass.UNKNOWN


def good_predecessors(class_graph: nx.DiGraph, node: str):
    """All predecessors following GOOD edges only."""
    for p in class_graph.predecessors(node):
        if edge_class(class_graph, p, node) == EdgeClass.GOOD:
            yield p


def good_successors(class_graph: nx.DiGraph, node):
    """All successors following GOOD edges only."""
    for s in class_graph.successors(node):
        if edge_class(class_graph, node, s) == EdgeClass.GOOD:
            yield s


class EdgeClassifier:
    def __init__(self, multi_graph: nx.MultiDiGraph) -> None:
        self.class_graph = nx.transitive_closure(
            nx.DiGraph(multi_graph.edges()))
        for _u, _v, data in self.class_graph.edges(data=True):
            data["eval"] = Evaluation(EdgeClass.UNKNOWN, None)

        for u, v, data in multi_graph.edges(data=True):
            if self.get_class(u, v) != EdgeClass.UNKNOWN:
                continue
            measurement = data["measurement"]
            if measurement.trust_reason:
                self.add_good_edge(u, v, measurement.trust_reason)
            else:
                ip = getattr(data["record"].data, "ip", None)
                if ip and not ip.is_global:
                    self.add_bad_edge(u, v, "Non global IP")

    def get_class(self, u: str, v: str) -> EdgeClass:
        return edge_class(self.class_graph, u, v)

    def mark_all_paths_good(self, u: str, v: str):
        """Mark all paths between u and v as GOOD.
        Assumes the input graph has all the edges from its transitive closure.
        """
        for s in self.class_graph.successors(u):
            if not self.class_graph.has_edge(s, v):
                continue
            self.add_good_edge(u, s, "On path for GOOD pair (%s, %s)" % (u, v))
            self.add_good_edge(s, v, "On path for GOOD pair (%s, %s)" % (u, v))

    def mark_new_connections_good(self, u, v):
        """Add new good connections from adding the GOOD edge u, v.
        Assumes the class_graph has all the edges from its transitive closure.
        """
        for p in chain([u], good_predecessors(self.class_graph, u)):
            path = [p]
            if p != u:
                path.append(u)
            for s in chain([v], good_successors(self.class_graph, v)):
                path.append(v)
                if s != v:
                    path.append(s)
                self.add_good_edge(
                    p, s, "Path (%s) is GOOD" % ", ".join(path))

    def add_good_edge(self, u: str, v: str, reason: str):
        if u == v or self.get_class(u, v) != EdgeClass.UNKNOWN:
            return
        self.class_graph[u][v]["eval"] = Evaluation(EdgeClass.GOOD, reason)
        self.mark_all_paths_good(u, v)
        self.mark_new_connections_good(u, v)
        # TODO: Mark all IP edges as GOOD if measurement is GOOD
        # Can do that by adding an extra node per measurement and
        # (ip, measurement_id) edges for last step

    def add_bad_edge(self, u: str, v: str, reason: str):
        if self.get_class(u, v) != EdgeClass.UNKNOWN:
            return
        self.class_graph[u][v]["eval"] = Evaluation(EdgeClass.BAD, reason)

    def unknown_edges(self):
        for u, v, edge_eval in self.class_graph.edges(data="eval"):
            if edge_eval.classification == EdgeClass.UNKNOWN:
                yield u, v


def classify_edges(multi_graph: nx.MultiDiGraph) -> nx.DiGraph:
    return EdgeClassifier(multi_graph).class_graph


def _get_edge_class(edge_data):
    try:
        return edge_data["eval"].classification
    except KeyError:
        return EdgeClass.UNKNOWN


def draw_graph(graph: nx.DiGraph):
    good_edges = set((u, v) for u, v, data in graph.edges(
        data=True) if _get_edge_class(data) == EdgeClass.GOOD)
    good_nodes = set(v for (u, v) in good_edges)
    bad_edges = set((u, v) for u, v, data in graph.edges(
        data=True) if _get_edge_class(data) == EdgeClass.BAD)
    bad_nodes = set(v for (u, v) in bad_edges)

    nodes_pos = nx.spring_layout(graph, random_state=RandomState(0))
    nx.draw_networkx_nodes(graph, pos=nodes_pos, alpha=0.6, node_color="gray")
    nx.draw_networkx_nodes(graph, pos=nodes_pos, alpha=0.8, nodelist=good_nodes, node_color="g")
    nx.draw_networkx_nodes(graph, pos=nodes_pos, alpha=0.8, nodelist=bad_nodes, node_color="r")
    nx.draw_networkx_labels(graph, pos=nodes_pos, font_size=8)
    nx.draw_networkx_edges(graph, pos=nodes_pos, alpha=0.25)
    nx.draw_networkx_edges(graph, edgelist=good_edges,
                           pos=nodes_pos, alpha=0.5, width=4, edge_color="g")
    nx.draw_networkx_edges(graph, edgelist=bad_edges,
                           pos=nodes_pos, alpha=0.5, width=4, edge_color="r")
