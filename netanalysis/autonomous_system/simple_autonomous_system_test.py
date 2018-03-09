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

import unittest

from . import simple_autonomous_system as sas


class NoneIpToAsnMap(sas.IpToAsnMap):
    def get_asn(self, ip_address):
        return None


class TestAsRepository(unittest.TestCase):
    def test_unknown_as(self):
        as_repo = sas.InMemoryAsRepository(NoneIpToAsnMap())
        asys = as_repo.get_as(999)
        self.assertIsNotNone(asys)
        self.assertEqual(999, asys.id)
        self.assertEqual("AS999", asys.name)

    def test_unknown_org(self):
        as_repo = sas.InMemoryAsRepository(NoneIpToAsnMap)
        org = as_repo.get_org("orgX")
        self.assertIsNotNone(org)
        self.assertEqual("orgX", org.id)

    def test_add_as(self):
        as_repo = sas.InMemoryAsRepository(NoneIpToAsnMap)
        as_repo.add_as("AS1", "First AS", "org1", "test_data", "sometime")
        as1 = as_repo.get_as("AS1")
        self.assertEqual("AS1", as1.id)
        self.assertEqual("First AS", as1.name)
        self.assertEqual("org1", as1.org.id)

    def test_add_org(self):
        as_repo = sas.InMemoryAsRepository(NoneIpToAsnMap)
        as_repo.add_org("org1", "First Org", "Country1",
                        "test_data", "sometime")
        org = as_repo.get_org("org1")
        self.assertEqual("org1", org.id)
        self.assertEqual("First Org", org.name)
        self.assertEqual("Country1", org.country)

    def test_as_org(self):
        as_repo = sas.InMemoryAsRepository(NoneIpToAsnMap)
        as_repo.add_as("AS1", "First AS", "org1", "test_data", "sometime")
        as_repo.add_org("org1", "First Org", "Country1",
                        "test_data", "sometime")
        org = as_repo.get_as("AS1").org
        self.assertEqual("org1", org.id)
        self.assertEqual("First Org", org.name)
        self.assertEqual("Country1", org.country)


class TestIpToAsnMap(unittest.TestCase):
    def test_default_data(self):
        ip_asn_map = sas.create_default_ip_asn_map()
        self.assertEqual(15169, ip_asn_map.get_asn("8.8.8.8"))
        self.assertEqual(15169, ip_asn_map.get_asn("8.8.4.4"))
        self.assertEqual(-1, ip_asn_map.get_asn("127.0.0.1"))


if __name__ == '__main__':
    unittest.main()
