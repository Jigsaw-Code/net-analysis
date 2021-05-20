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
import json
import unittest

from .measurement import Measurement

# Spec at https://github.com/ooni/spec/blob/master/nettests/ts-017-web-connectivity.md
_TEST_JSON = '''
{
  "test_keys": {
    "queries": [
      {
        "resolver_hostname": null,
        "query_type": "A",
        "hostname": "twitter.com",
        "answers": [
          {
            "ipv4": "104.244.42.129",
            "answer_type": "A"
          },
          {
            "ipv4": "104.244.42.1",
            "answer_type": "A"
          }
        ],
        "failure": null,
        "resolver_port": null
      }
    ]
  },
  "measurement_start_time": "2020-10-29 09:29:07",
  "test_start_time": "2020-10-29 07:45:02",
  "probe_asn": "AS50810",
  "input": "http://twitter.com/",
  "probe_ip": "127.0.0.1",
  "report_id": "20201029T074503Z_webconnectivity_IR_50810_n1_mYbv8gqRSd4sEkTj",
  "probe_city": null,
  "id": "75053b70-9ea5-4e14-a590-d394f9ff0c8b",
  "probe_cc": "IR"
}
'''


class TestMeasurement(unittest.TestCase):
    def test_example(self):
        m = Measurement(json.loads(_TEST_JSON))
        self.assertEqual(dt.datetime(2020, 10, 29, 9, 29, 7, tzinfo=dt.timezone.utc), m.time)
        self.assertEqual('twitter.com', m.hostname)
        self.assertEqual('IR', m.country)
        self.assertEqual(50810, m.asn)
        self.assertEqual(0, m.resolver_asn)
        self.assertEqual(
            'https://explorer.ooni.org/measurement/20201029T074503Z_webconnectivity_IR_50810_n1_mYbv8gqRSd4sEkTj?input=http%3A%2F%2Ftwitter.com%2F',
            m.explorer_url
        )

    def test_time(self):
        m = Measurement({'measurement_start_time':  '2020-10-29 09:29:07'})
        self.assertEqual(dt.datetime(2020, 10, 29, 9, 29, 7, tzinfo=dt.timezone.utc), m.time)

    def test_hostname_with_scheme(self):
        m = Measurement({'input': 'https://youtube.com'})
        self.assertEqual('youtube.com', m.hostname)

    def test_hostname_no_scheme(self):
        m = Measurement({'input': 'youtube.com'})
        self.assertEqual('youtube.com', m.hostname)

    def test_country(self):
        m = Measurement({'probe_cc': 'TR'})
        self.assertEqual('TR', m.country)

    def test_asn(self):
        m = Measurement({'probe_asn': 'AS1234'})
        self.assertEqual(1234, m.asn)

    def test_asn_missing(self):
        m = Measurement({})
        self.assertEqual(0, m.asn)

    def test_resolver_ip(self):
        m = Measurement({'test_keys': {'client_resolver': '74.125.47.144'}})
        self.assertEqual(ip_address('74.125.47.144'), m.resolver_ip)

    def test_get(self):
        m = Measurement({'test_keys': {'dns_experiment_failure': 'dns_nxdomain'}})
        self.assertEqual('dns_nxdomain', m.get(['test_keys', 'dns_experiment_failure'], 'MISSING'))

    def test_get_step_missing(self):
        m = Measurement({})
        self.assertEqual('MISSING', m.get(['test_keys', 'dns_experiment_failure'], 'MISSING'))

    def test_get_step_null(self):
        m = Measurement({'test_keys': None})
        self.assertEqual('MISSING', m.get(['test_keys', 'dns_experiment_failure'], 'MISSING'))

    def test_get_last_missing(self):
        m = Measurement({'test_keys': {}})
        self.assertEqual('MISSING', m.get(['test_keys', 'dns_experiment_failure'], 'MISSING'))

    def test_get_last_null(self):
        m = Measurement({'test_keys': {'dns_experiment_failure': None}})
        self.assertEqual('MISSING', m.get(['test_keys', 'dns_experiment_failure'], 'MISSING'))


if __name__ == '__main__':
    unittest.main()
