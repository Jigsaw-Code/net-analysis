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
import gzip
from typing import Dict

import geoip2.database

from netanalysis.infrastructure.resources import resource_filename

from . import model

class SimpleAutonomousSystem(model.AutonomousSystem):
    def __init__(self, as_repo: model.AsRepository, as_number: int, as_name: str, org_id: str,
                 source: str, date_changed_str: str) -> None:
        self._as_repo = as_repo
        self._id = as_number
        self._name = as_name
        self._org_id = org_id
        self.source = source
        self.date_changed_str = date_changed_str
        self._type = model.AsType.UNKNOWN

    @property
    def id(self): return self._id

    @property
    def name(self): return self._name

    @property
    def type(self): return self._type

    @type.setter
    def type(self, new_type): self._type = new_type

    @property
    def org(self):
        return self._as_repo.get_org(self._org_id)

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)


def UnknownAutonomousSystem(as_repo, as_number):
    return SimpleAutonomousSystem(as_repo, as_number, "AS%d" % as_number, None, None, None)


def UnknownAsOrg(org_id):
    return model.AsOrg(org_id, org_id, None, None, None)



class InMemoryAsRepository(model.AsRepository):
    def __init__(self) -> None:
        self.id_as = {}  # type: Dict[int, model.AutonomousSystem]
        self.id_org = {}  # type: Dict[str, model.AsOrg]

    def add_as(self, as_number: int, as_name: str, org_id: str,
               source: str, date_changed_str: str) -> None:
        self.id_as[as_number] = SimpleAutonomousSystem(
            self, as_number, as_name, org_id, source, date_changed_str)

    def add_org(self, org_id: str, org_name: str, org_country: str,
                source: str, date_changed_str: str) -> None:
        self.id_org[org_id] = model.AsOrg(
            org_id, org_name, org_country, source, date_changed_str)

    def get_as(self, as_number: int) -> model.AutonomousSystem:
        autonomous_system = self.id_as.get(as_number)
        if not autonomous_system:
            return UnknownAutonomousSystem(self, as_number)
        return autonomous_system

    def get_org(self, org_id: str) -> model.AsOrg:
        org = self.id_org.get(org_id)
        if not org:
            return UnknownAsOrg(org_id)
        return org


def fill_as_info_from_filename(as_org_filename: str, as_repo: InMemoryAsRepository):
    with gzip.open(as_org_filename, "rt") as as_file:
        return fill_as_info_from_file(as_file, as_repo)


def fill_as_info_from_file(as_org_file, as_repo: InMemoryAsRepository):
    mode = None
    while True:
        line = as_org_file.readline()
        if len(line) == 0:
            break
        line = line.strip()
        if not line or line[0] == "#":
            if line.startswith("# format:org_id"):
                mode = "org"
            elif line.startswith("# format:aut"):
                mode = "as"
            continue
        if mode == "as":
            as_number_str, date_changed_str, as_name, org_id, source = \
                line.split("|")
            as_number = int(as_number_str)
            as_repo.add_as(as_number, as_name, org_id,
                           source, date_changed_str)
        elif mode == "org":
            org_id, date_changed_str, org_name, org_country, source = \
                line.split("|")
            as_repo.add_org(org_id, org_name, org_country,
                            source, date_changed_str)


def fill_as_type_from_filename(filename: str, as_repo: InMemoryAsRepository):
    with gzip.open(filename, "rt") as as_type_file:
        fill_as_type_from_file(as_type_file, as_repo)


def fill_as_type_from_file(as_type_file, as_repo: InMemoryAsRepository):
    str_to_type = {
        "Content": model.AsType.CONTENT,
        "Enterpise": model.AsType.ENTERPRISE,
        "Transit/Access": model.AsType.TRANSIT_ACCESS,
    }
    for line in as_type_file:
        line = line.strip()
        if not line or line[0] == "#":
            continue
        as_number_str, _source, as_type_str = line.split("|")
        as_number = int(as_number_str)
        asys = as_repo.get_as(as_number)
        if asys:
            asys.type = str_to_type[as_type_str]


def create_default_as_repo() -> InMemoryAsRepository:
    as_repo = InMemoryAsRepository()

    as_info_filename = resource_filename(
        "third_party/caida.org/as-organizations/20170401.as-org2info.txt.gz")
    fill_as_info_from_filename(as_info_filename, as_repo)

    as_type_filename = resource_filename(
        "third_party/caida.org/as-classification/20150801.as2types.txt.gz")
    fill_as_type_from_filename(as_type_filename, as_repo)
    return as_repo
