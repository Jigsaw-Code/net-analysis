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

import datetime as dt
import ipaddress
import typing as ty

from netanalysis.ooni.measurement import Measurement


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
    answers: ty.List[ty.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]
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
    ],
    'NXDOMAIN': [
        'unknown_failure: lookup [DOMAIN]: No address associated with hostname',
        'dns_nxdomain_error',
        'dns_name_error',
    ],
})


def make_status(domain: str, failure: str) -> str:
    generic_failure = failure.replace(domain, '[DOMAIN]')
    return _ERROR_TXT_TO_CODE.get(generic_failure, generic_failure)


def get_observations(m: Measurement) -> ty.List[DnsObservation]:
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
        return [obs_tmpl._replace(failure=failure, status='MISSING_QUERIES')]
    observations = []
    for query in queries:
        query_type = query.get('query_type')
        if query_type not in ('A', 'AAAA'):
            continue
        failure = query.get('failure')
        if failure:
            observation = obs_tmpl._replace(query_type=query_type, failure=failure, status=make_status(domain, failure))
        else:
            # This drops all CNAME answers
            answers = [ipaddress.ip_address(a.get('ipv4', a.get('ipv6')))
                       for a in query.get('answers', []) if a['answer_type'] == query_type]
            observation = obs_tmpl._replace(query_type=query_type, status='OK', answers=answers)
        observations.append(observation)
    return observations


class Evaluator:
    def __init__(self):
        self._errors: set[ty.Tuple[str,  str]] = set()
        self._ips: set = set()

    def add_control(self, m: Measurement):
        domain = m.hostname
        failure = m.get(['test_keys', 'control', 'dns', 'failure'])
        if failure:
            self._errors.add((domain, make_status(domain, failure)))
            return
        addresses = m.get(['test_keys', 'control', 'dns', 'addrs'])
        if addresses:
            self._errors.add((domain, 'OK'))
            for address_str in addresses:
                try:
                    ip = ipaddress.ip_address(address_str)
                    self._ips.add((domain, ip))
                except:
                    pass

    def evaluate(self, domain: str, status: str, answers: ty.Iterable[ty.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]):
        if status == 'OK':
            for answer in answers:
                if not answer.is_global:
                    return 'BAD_NON_GLOBAL_IP'
                if (domain, answer) in self._ips:
                    return 'OK_MATCHES_CONTROL_IP'
            return 'INCONCLUSIVE_CHECK_IPS'

        if (domain, status) in self._errors:
            return 'OK_MATCHES_CONTROL_ERROR'
        if (domain, 'OK') not in self._errors:
            return 'INCONCLUSIVE_BAD_CONTROL'
        return f'BAD_STATUS_{status}'
