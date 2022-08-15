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

import unittest

from . import dns
from netanalysis.ooni.measurement import Measurement


class TestDns(unittest.TestCase):
    def test_make_status(self):
        self.assertEqual(
            dns.make_status('twitter.com', 'unknown_failure: lookup twitter.com: getaddrinfow'),
            dns.make_status('youtube.com', 'unknown_failure: lookup youtube.com: getaddrinfow'))

        self.assertEqual('NXDOMAIN',
                         dns.make_status('youtube.com', 'unknown_failure: lookup youtube.com: No address associated with hostname'))
        self.assertEqual('SERVFAIL',
                         dns.make_status('twitter.com', 'unknown_failure: lookup twitter.com: getaddrinfow: This is usually a temporary error during hostname resolution and means that the local server did not receive a response from an authoritative server.'))

    def test_evaluator(self):
        evaluator = dns.Evaluator()
        evaluator.add_control(Measurement({
            'input': 'https://badsite.com',
            'test_keys': {
                'control': {
                    'dns': {'failure': 'dns_nxdomain_error'}
                }
            },
        }))
        self.assertEqual('OK_MATCHES_CONTROL_ERROR', evaluator.evaluate('badsite.com', 'NXDOMAIN', []))


if __name__ == '__main__':
    unittest.main()
