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

import abc
from collections import namedtuple
from enum import Enum
import ipaddress
from typing import Union

IpAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]

AsOrg = namedtuple("AsOrg", ["id", "name", "country", "source", "date_changed_str"])

class AsType(Enum):
    UNKNOWN = 0
    CONTENT = 1
    ENTERPRISE = 1
    TRANSIT_ACCESS = 2


class AutonomousSystem(abc.ABC):
    @abc.abstractmethod
    def id(self) -> int: pass
    @abc.abstractmethod
    def name(self) -> str: pass
    @abc.abstractmethod
    def org(self) -> AsOrg: pass
    @abc.abstractmethod
    def type(self) -> AsType: pass


class AsRepository(abc.ABC):
    @abc.abstractmethod
    def get_as(self, as_number: int) -> AutonomousSystem:
        pass
