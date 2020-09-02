import unittest

from ipaddress import ip_address as ip

from . import ip_info as ii

localhost_ip4 = ip("127.0.0.1")
localhost_ip6 = ip("::1")

# Google DNS addresses will be stably assigned to Google's AS"
google_dns_ip4_8888 = ip("8.8.8.8")
google_dns_ip4_8844 = ip("8.8.4.4")
google_dns_ip6_8888 = ip("2001:4860:4860::8888")
google_dns_ip6_8844 = ip("2001:4860:4860::8844")
google_asn = 15169


class TestIpInfo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ip_service = ii.create_default_ip_info_service()

    def test_ip4_to_as(self):
        self.assertEqual(google_asn, self._ip_service.get_as(
            google_dns_ip4_8888).id)
        self.assertEqual(google_asn, self._ip_service.get_as(
            google_dns_ip4_8888).id)
        self.assertEqual(-1, self._ip_service.get_as(localhost_ip4).id)

    def test_ip6_to_as(self):
        self.assertEqual(google_asn, self._ip_service.get_as(
            google_dns_ip6_8888).id)
        self.assertEqual(google_asn, self._ip_service.get_as(
            google_dns_ip6_8844).id)
        self.assertEqual(-1, self._ip_service.get_as(localhost_ip6).id)

    def test_ip4_to_country(self):
        # nycourts.gov
        self.assertEqual(("US", "United States"),
                         self._ip_service.get_country(ip("207.29.128.60")))
        # Technical Research Centre of Finland
        self.assertEqual(("FI", "Finland"),
                         self._ip_service.get_country(ip("130.188.0.0")))
        self.assertEqual(("ZZ", "Unknown"),
                         self._ip_service.get_country(localhost_ip4))

    def test_ip6_to_country(self):
        # Instituto Costarricense de Electricidad y Telecom
        self.assertEqual(("CR", "Costa Rica"), self._ip_service.get_country(
            ip("2001:1330::")))
        # Wikimedia Foundation
        self.assertEqual(("US", "United States"), self._ip_service.get_country(
            ip("2620:62:c000::")))
        self.assertEqual(("ZZ", "Unknown"),
                         self._ip_service.get_country(localhost_ip6))

    def test_resolve_ip4(self):
        self.assertEqual(
            "dns.google", self._ip_service.resolve_ip(google_dns_ip4_8888))
        self.assertEqual(
            "dns.google", self._ip_service.resolve_ip(google_dns_ip4_8888))
        self.assertEqual(
            "localhost", self._ip_service.resolve_ip(localhost_ip4))

    def test_resolve_ip6(self):
        self.assertEqual("dns.google", self._ip_service.resolve_ip(
            google_dns_ip6_8888))
        self.assertEqual("dns.google", self._ip_service.resolve_ip(
            google_dns_ip6_8844))
        self.assertEqual(
            "localhost", self._ip_service.resolve_ip(localhost_ip6))


if __name__ == '__main__':
    unittest.main()
