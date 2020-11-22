#!/usr/bin/python
#
# Copyright 2020 Jigsaw Operations LLC
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
import collections
import datetime as dt
import ipaddress
import socket
import typing as ty
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Union

from netanalysis.ooni.measurement import Measurement

IpAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


class DnsPath(NamedTuple):
    cnames: List['Domain']
    ips: List[IpAddress]


class Domain:
    def __init__(self, domain_name) -> None:
        self.name = domain_name
        self._cnames: set[Domain] = set()
        self._ips: set[IpAddress] = set()

    def __repr__(self) -> str:
        return f'Domain({repr(self.name)})'

    def add_path(self, dns_path: DnsPath):
        if dns_path.cnames:
            cname = dns_path.cnames[0]
            self._cnames.add(cname)
            cname.add_path(dns_path._replace(cnames=dns_path.cnames[1:]))
        else:
            self._ips.update(dns_path.ips)

    def path_matches_control(self, dns_path: DnsPath, visited: Optional[Set['Domain']] = None) -> str:
        if visited is None:
            visited = set()
        if self in visited:
            return False
        visited.add(self)

        for ip in dns_path.ips:
            if ip in self._ips:
                return True

        for cname in self._cnames:
            if cname.path_matches_control(dns_path, visited=visited):
                return True
        return False

    def path_is_valid(self, dns_path: DnsPath) -> str:
        # TODO: Error
        for ip in dns_path.ips:
            if not ip.is_global:
                return 'BAD_NON_GLOBAL_IP'

        if self.path_matches_control(dns_path):
            self.add_path(dns_path)
            return 'OK_MATCHES_CONTROL'

        # Try local resolution and TLS. Should persist resolutions.
        return 'INCONCLUSIVE_CHECK_IPS'


class DomainRepository:
    def __init__(self) -> None:
        self._domains: Dict[str, Domain] = dict()

    def get(self, domain_name: str) -> Domain:
        return self._domains.setdefault(domain_name, Domain(domain_name))


def resolve(domains: DomainRepository, domain_name: str) -> Iterable[DnsPath]:
    cnames = []
    ips = []
    for _, _, _, cname, sockaddr in socket.getaddrinfo(
            domain_name, None, proto=socket.IPPROTO_TCP, flags=socket.AI_CANONNAME):
        if cname and cname != domain_name:
            cnames = [cname]
        ips.append(ipaddress.ip_address(sockaddr[0]))
    return DnsPath([domains.get(c) for c in cnames], ips)


class DnsObservation(ty.NamedTuple):
    time: dt.datetime
    client_country: str
    client_asn: int
    resolver_ip: ty.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
    resolver_asn: int
    domain: str
    query_type: str
    failure: str
    status: str
    answers: DnsPath
    explorer_url: str


def _make_error_map(errors):
    map = {}
    for key, values in errors.items():
        for value in values:
            map[value] = key
    return map


# This can help: https://github.com/ooni/spec/blob/master/data-formats/df-007-errors.md
_ERROR_TXT_TO_CODE = _make_error_map({
    'SERVFAIL': [
        'unknown_failure: lookup [DOMAIN]: getaddrinfow: This is usually a temporary error during hostname resolution and means that the local server did not receive a response from an authoritative server.',
        'unknown_failure: lookup [DOMAIN] on [scrubbed]: server misbehaving',
        'dns_server_failure',
    ],
    'NXDOMAIN': [
        'unknown_failure: lookup [DOMAIN]: No address associated with hostname',
        'dns_nxdomain_error',
        'dns_name_error',
    ],
})


def make_status(domain: str, failure: str) -> str:
    if not failure:
        return 'INCONCLUSIVE_MISSING_FAILURE'
    generic_failure = failure.replace(domain, '[DOMAIN]')
    return _ERROR_TXT_TO_CODE.get(generic_failure, generic_failure)


def get_observations(domains: DomainRepository, m: Measurement) -> ty.List[DnsObservation]:
    domain = m.hostname
    try:
        ipaddress.ip_address(domain)
        return []
    except ValueError:
        pass
    obs_tmpl = DnsObservation(time=m.time, client_country=m.country, client_asn=m.asn,
                              resolver_ip=m.resolver_ip, resolver_asn=m.resolver_asn,
                              domain=domain, query_type=None, failure=None, status=None,
                              answers=None, explorer_url=m.explorer_url)
    queries = m.get(["test_keys", "queries"], [])
    # If the query fails, OONI doesn't output any query.
    if not queries:
        failure = m.get(['test_keys', 'dns_experiment_failure'])  # NODATA?
        status = make_status(domain, failure)
        return [obs_tmpl._replace(failure=failure, status=status)]
    observations = []
    for query in queries:
        query_type = query.get('query_type')
        if query_type not in ('A', 'AAAA'):
            continue
        failure = query.get('failure')
        if failure:
            observation = obs_tmpl._replace(query_type=query_type, failure=failure, status=make_status(domain, failure))
        else:
            cnames = []
            ips = []
            for answer in query.get('answers', []):
                if answer.get('answer_type') == 'CNAME':
                    cname_str = answer['hostname']
                    if cname_str != domain:
                        cnames.append(domains.get(cname_str))
                elif answer.get('answer_type') in ('A', 'AAAA'):
                    ip = ipaddress.ip_address(answer.get('ipv4', answer.get('ipv6')))
                    ips.append(ip)
            dns_path = DnsPath(cnames, ips)
            observation = obs_tmpl._replace(query_type=query_type, status='OK', answers=dns_path)
        observations.append(observation)
    return observations


class Evaluator:
    def __init__(self, domains: DomainRepository):
        self._errors: set[ty.Tuple[str,  str]] = set()
        self._domains = domains

    def add_control(self, m: Measurement):
        domain = m.hostname
        failure = m.get(['test_keys', 'control', 'dns', 'failure'])
        if failure:
            self._errors.add((domain, make_status(domain, failure)))
            return
        addresses = m.get(['test_keys', 'control', 'dns', 'addrs'])
        if addresses:
            self._errors.add((domain, 'OK'))
            cnames = []
            ips = []
            for address_str in addresses:
                try:
                    ip = ipaddress.ip_address(address_str)
                    ips.append(ip)
                except:
                    if address_str != domain:
                        cnames.append(self._domains.get(address_str))
            self._domains.get(domain).add_path(DnsPath(cnames, ips))

    def evaluate(self, domain_name: str, status: str, dns_path: DnsPath):
        if status == 'OK':
            return self._domains.get(domain_name).path_is_valid(dns_path)
        if (domain_name, status) in self._errors:
            return 'OK_MATCHES_CONTROL_ERROR'
        if (domain_name, 'OK') not in self._errors:
            return 'INCONCLUSIVE_BAD_CONTROL'
        return f'BAD_STATUS_{status}'
