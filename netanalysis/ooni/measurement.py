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
from ipaddress import ip_address
from typing import Any, List
import urllib.parse as up

# Base format specified at https://github.com/ooni/spec/blob/master/data-formats/df-000-base.md


class Measurement:
    def __init__(self, measurement: dict) -> None:
        self.data = measurement

    @property
    def time(self) -> dt.datetime:
        time_str = self.data['measurement_start_time']
        return dt.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)

    @property
    def hostname(self) -> str:
        parsed_url = up.urlparse(self.data['input'])
        if not parsed_url.scheme:
            parsed_url = up.urlparse(f'''//{self.data['input']}''')
        return parsed_url.hostname

    @property
    def country(self) -> str:
        return self.data['probe_cc']

    @property
    def asn(self) -> int:
        return int(self.data.get('probe_asn', 'AS0')[2:])

    @property
    def asn(self) -> int:
        return int(self.data.get('probe_asn', 'AS0')[2:])

    @property
    def resolver_asn(self) -> int:
        return int(self.data.get('resolver_asn', 'AS0')[2:])

    @property
    def resolver_ip(self) -> int:
        ip_str = self.data['test_keys'].get('client_resolver')
        return ip_address(ip_str) if ip_str else None

    @property
    def explorer_url(self) -> str:
        return f'''https://explorer.ooni.org/measurement/{self.data['report_id']}?{up.urlencode({'input': self.data['input']})}'''

    def get(self, path: List[str], default: Any = None):
        value = self.data
        for key in path:
            try:
                value = value[key]
            except (KeyError, TypeError):
                return default
        if value is None:
            return default
        return value
