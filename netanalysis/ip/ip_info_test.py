import unittest

from ipaddress import ip_address as ip

from . import ip_info as ii

# Google DNS addresses will be stably assigned to Google's AS"
GOOGLE_DNS_IP4_8888 = ip("8.8.8.8")
GOOGLE_DNS_IP4_8844 = ip("8.8.4.4")
GOOGLE_DNS_IP6_8888 = ip("2001:4860:4860::8888")
GOOGLE_DNS_IP6_8844 = ip("2001:4860:4860::8844")
GOOGLE_ASN = 15169


class TestIpInfo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ip_service = ii.create_default_ip_info_service()

    def test_ip4_to_as(self):
        self.assertEqual(GOOGLE_ASN, self._ip_service.get_as(
            GOOGLE_DNS_IP4_8888).id)
        self.assertEqual(GOOGLE_ASN, self._ip_service.get_as(
            GOOGLE_DNS_IP4_8888).id)
        self.assertEqual(-1, self._ip_service.get_as(ip("127.0.0.1")).id)

    def test_ip6_to_as(self):
        self.assertEqual(GOOGLE_ASN, self._ip_service.get_as(
            GOOGLE_DNS_IP6_8888).id)
        self.assertEqual(GOOGLE_ASN, self._ip_service.get_as(
            GOOGLE_DNS_IP6_8844).id)
        self.assertEqual(-1, self._ip_service.get_as(ip("::1")).id)

    def test_ip4_to_country(self):
        # nycourts.gov
        self.assertEqual(("US", "United States"),
                         self._ip_service.get_country(ip("207.29.128.60")))
        # Technical Research Centre of Finland
        self.assertEqual(("FI", "Finland"),
                         self._ip_service.get_country(ip("130.188.0.0")))
        self.assertEqual(("ZZ", "Unknown"),
                         self._ip_service.get_country(ip("127.0.0.1")))

    def test_ip6_to_country(self):
        # Instituto Costarricense de Electricidad y Telecom
        self.assertEqual(("CR", "Costa Rica"), self._ip_service.get_country(
            ip("2001:1330::")))
        # Wikimedia Foundation
        self.assertEqual(("US", "United States"), self._ip_service.get_country(
            ip("2620:62:c000::")))
        self.assertEqual(("ZZ", "Unknown"),
                         self._ip_service.get_country(ip("::1")))

    def test_resolve_ip4(self):
        self.assertEqual(
            "dns.google", self._ip_service.resolve_ip(GOOGLE_DNS_IP4_8888))
        self.assertEqual(
            "dns.google", self._ip_service.resolve_ip(GOOGLE_DNS_IP4_8888))
        self.assertEqual(
            "localhost", self._ip_service.resolve_ip(ip("127.0.0.1")))

    def test_resolve_ip6(self):
        self.assertEqual("dns.google", self._ip_service.resolve_ip(
            GOOGLE_DNS_IP6_8888))
        self.assertEqual("dns.google", self._ip_service.resolve_ip(
            GOOGLE_DNS_IP6_8844))
        self.assertEqual(
            "localhost", self._ip_service.resolve_ip(ip("::1")))


if __name__ == '__main__':
    unittest.main()
