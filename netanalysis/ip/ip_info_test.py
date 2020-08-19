import unittest

from ipaddress import ip_address as ip

from . import ip_info as ii


class TestIpInfo(unittest.TestCase):
  def test_ip4(self):
    ip_asn_map = ii.create_default_ip_info_service()
    self.assertEqual(15169, ip_asn_map.get_as(ip("8.8.8.8")).id)
    self.assertEqual(15169, ip_asn_map.get_as(ip("8.8.4.4")).id)
    self.assertEqual(-1, ip_asn_map.get_as(ip("127.0.0.1")).id)
  
  def test_ip6(self):
    ip_asn_map = ii.create_default_ip_info_service()
    ip_asn_map = ii.create_default_ip_info_service()
    self.assertEqual(15169, ip_asn_map.get_as(ip("2001:4860:4860::8888")).id)
    self.assertEqual(15169, ip_asn_map.get_as(ip("2001:4860:4860::8844")).id)
    self.assertEqual(-1, ip_asn_map.get_as(ip("::1")).id)

if __name__ == '__main__':
  unittest.main()
