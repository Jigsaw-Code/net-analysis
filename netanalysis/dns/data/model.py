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

import datetime
from ipaddress import ip_address, IPv4Address, IPv6Address
from typing import List, Union


class RecordData:
    """Represents the data in a DNS Resource Record."""

    def __repr__(self):
        return "%s(%s)" % (self.__class__, str(self.__dict__))


class IpAddressData(RecordData):
    """Data for Resource Record type A or AAAA"""

    def __init__(self, ip_str: str) -> None:
        self._ip = ip_address(ip_str)

    @property
    def ip(self):
        return self._ip


class CnameData(RecordData):
    """Data for Resource Record type CNAME"""

    def __init__(self, cname: str) -> None:
        self._cname = cname

    @property
    def cname(self):
        return self._cname


class ResourceRecord:
    def __init__(self, name: str, data: RecordData, ttl: datetime.timedelta=None) -> None:
        if not name:
            raise ValueError("ResourceRecord requires name")
        self.name = name
        self.data = data
        self.ttl = ttl
        if not isinstance(ttl, (type(None), datetime.timedelta)):
            raise ValueError("ttl must be of type datetime.timedelta. Found type %s, value %s" % (
                type(ttl), repr(ttl)))

    def __repr__(self):
        return "%s(%s)" % (self.__class__, str(self.__dict__))


class DnsMeasurement:
    def __init__(self,
                 measurement_id: str,
                 time: datetime.datetime,
                 records: List[ResourceRecord],
                 resolver_ip: Union[IPv4Address, IPv6Address]=None,
                 client_asn: int=None,
                 client_country: str=None,
                 provenance: str=None,
                 trust_reason: str=None) -> None:
        self.measurement_id = measurement_id
        self.time = time
        self.records = records
        self.resolver_ip = resolver_ip
        self.client_asn = client_asn
        self.client_country = client_country
        self.provenance = provenance
        self.trust_reason = trust_reason
    
    def __repr__(self):
        return "DnsMeasurement(%s)" % str(self.__dict__)
