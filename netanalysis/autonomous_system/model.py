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

"""
Modelling of BGP Autonomous Systems and related concepts.
"""

import abc
from collections import namedtuple
from enum import Enum

AsOrg = namedtuple(
    "AsOrg", ["id", "name", "country", "source", "date_changed_str"])


class AsType(Enum):
    "Type of the Autonomous System"
    UNKNOWN = 0
    CONTENT = 1
    ENTERPRISE = 1
    TRANSIT_ACCESS = 2


class AutonomousSystem(abc.ABC):
    """
    Represents an Autonomous System on the Internet
    """

    @abc.abstractmethod
    def number(self) -> int:
        "The number of this AS"
        pass

    @abc.abstractmethod
    def name(self) -> str:
        "The name of this AS"
        pass

    @abc.abstractmethod
    def org(self) -> AsOrg:
        "The organization that owns this AS"
        pass

    @abc.abstractmethod
    def type(self) -> AsType:
        "The type of this AS"
        pass


class AsRepository(abc.ABC):
    """
    Provides ways to query for ASes.
    """
    @abc.abstractmethod
    def get_as(self, as_number: int) -> AutonomousSystem:
        "Gets the AS with the given number"
        pass

    @abc.abstractmethod
    def get_as_for_ip(self, ip_address_str: str) -> AutonomousSystem:
        "Gets the AS that owns the given IP address"
        pass
