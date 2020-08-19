import unittest

from ipaddress import ip_address as ip

from . import ip_info as ii


class TestIpInfo(unittest.TestCase):
  def test_ip4_to_as(self):
    ip_service = ii.create_default_ip_info_service()
    self.assertEqual(15169, ip_service.get_as(ip("8.8.8.8")).id)
    self.assertEqual(15169, ip_service.get_as(ip("8.8.4.4")).id)
    self.assertEqual(-1, ip_service.get_as(ip("127.0.0.1")).id)
  
  def test_ip6_to_as(self):
    ip_service = ii.create_default_ip_info_service()
    self.assertEqual(15169, ip_service.get_as(ip("2001:4860:4860::8888")).id)
    self.assertEqual(15169, ip_service.get_as(ip("2001:4860:4860::8844")).id)
    self.assertEqual(-1, ip_service.get_as(ip("::1")).id)

  def test_ip4_to_country(self):
    ip_service = ii.create_default_ip_info_service()
    self.assertEqual(("US", "United States"), ip_service.get_country(ip("8.8.8.8")))
    self.assertEqual(("US", "United States"), ip_service.get_country(ip("8.8.4.4")))
    self.assertEqual(("ZZ", "Unknown"), ip_service.get_country(ip("127.0.0.1")))

  def test_ip6_to_country(self):
    ip_service = ii.create_default_ip_info_service()
    self.assertEqual(("US", "United States"), ip_service.get_country(ip("2001:4860:4860::8888")))
    self.assertEqual(("US", "United States"), ip_service.get_country(ip("2001:4860:4860::8844")))
    self.assertEqual(("ZZ", "Unknown"), ip_service.get_country(ip("::1")))
  
  def test_resolve_ip4(self):
    ip_service = ii.create_default_ip_info_service()
    self.assertEqual("dns.google", ip_service.resolve_ip(ip("8.8.8.8")))
    self.assertEqual("dns.google", ip_service.resolve_ip(ip("8.8.4.4")))
    self.assertEqual("localhost", ip_service.resolve_ip(ip("127.0.0.1")))

  def test_resolve_ip4(self):
    ip_service = ii.create_default_ip_info_service()
    self.assertEqual("dns.google", ip_service.resolve_ip(ip("2001:4860:4860::8888")))
    self.assertEqual("dns.google", ip_service.resolve_ip(ip("2001:4860:4860::8844")))
    self.assertEqual("localhost", ip_service.resolve_ip(ip("::1")))


if __name__ == '__main__':
  unittest.main()
