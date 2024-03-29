"""
Integration tests for stem.descriptor.server_descriptor.
"""

from __future__ import with_statement

import datetime
import os
import unittest

import stem.control
import stem.descriptor.server_descriptor
import stem.exit_policy
import stem.version
import test.integ.descriptor
import test.runner

class TestServerDescriptor(unittest.TestCase):
  def test_metrics_descriptor(self):
    """
    Parses and checks our results against a server descriptor from metrics.
    """
    
    descriptor_path = test.integ.descriptor.get_resource("example_descriptor")
    
    descriptor_file = open(descriptor_path)
    descriptor_file.readline() # strip header
    descriptor_contents = descriptor_file.read()
    descriptor_file.close()
    
    expected_family = [
      "$0CE3CFB1E9CC47B63EA8869813BF6FAB7D4540C1",
      "$1FD187E8F69A9B74C9202DC16A25B9E7744AB9F6",
      "$74FB5EFA6A46DE4060431D515DC9A790E6AD9A7C",
      "$77001D8DA9BF445B0F81AA427A675F570D222E6A",
      "$B6D83EC2D9E18B0A7A33428F8CFA9C536769E209",
      "$D2F37F46182C23AB747787FD657E680B34EAF892",
      "$E0BD57A11F00041A9789577C53A1B784473669E4",
      "$E5E3E9A472EAF7BE9682B86E92305DB4C71048EF",
    ]
    
    expected_onion_key = """-----BEGIN RSA PUBLIC KEY-----
MIGJAoGBAJv5IIWQ+WDWYUdyA/0L8qbIkEVH/cwryZWoIaPAzINfrw1WfNZGtBmg
skFtXhOHHqTRN4GPPrZsAIUOQGzQtGb66IQgT4tO/pj+P6QmSCCdTfhvGfgTCsC+
WPi4Fl2qryzTb3QO5r5x7T8OsG2IBUET1bLQzmtbC560SYR49IvVAgMBAAE=
-----END RSA PUBLIC KEY-----"""
    
    expected_signing_key = """-----BEGIN RSA PUBLIC KEY-----
MIGJAoGBAKwvOXyztVKnuYvpTKt+nS3XIKeO8dVungi8qGoeS+6gkR6lDtGfBTjd
uE9UIkdAl9zi8/1Ic2wsUNHE9jiS0VgeupITGZY8YOyMJJ/xtV1cqgiWhq1dUYaq
51TOtUogtAPgXPh4J+V8HbFFIcCzIh3qCO/xXo+DSHhv7SSif1VpAgMBAAE=
-----END RSA PUBLIC KEY-----"""
    
    expected_signature = """-----BEGIN SIGNATURE-----
dskLSPz8beUW7bzwDjR6EVNGpyoZde83Ejvau+5F2c6cGnlu91fiZN3suE88iE6e
758b9ldq5eh5mapb8vuuV3uO+0Xsud7IEOqfxdkmk0GKnUX8ouru7DSIUzUL0zqq
Qlx9HNCqCY877ztFRC624ja2ql6A2hBcuoYMbkHjcQ4=
-----END SIGNATURE-----"""
    
    desc = stem.descriptor.server_descriptor.RelayDescriptor(descriptor_contents)
    self.assertEquals("caerSidi", desc.nickname)
    self.assertEquals("A7569A83B5706AB1B1A9CB52EFF7D2D32E4553EB", desc.fingerprint)
    self.assertEquals("71.35.133.197", desc.address)
    self.assertEquals(9001, desc.or_port)
    self.assertEquals(None, desc.socks_port)
    self.assertEquals(None, desc.dir_port)
    self.assertEquals("Tor 0.2.1.30 on Linux x86_64", desc.platform)
    self.assertEquals(stem.version.Version("0.2.1.30"), desc.tor_version)
    self.assertEquals("Linux x86_64", desc.operating_system)
    self.assertEquals(588217, desc.uptime)
    self.assertEquals(datetime.datetime(2012, 3, 1, 17, 15, 27), desc.published)
    self.assertEquals("www.atagar.com/contact", desc.contact)
    self.assertEquals(["1", "2"], desc.link_protocols)
    self.assertEquals(["1"], desc.circuit_protocols)
    self.assertEquals(False, desc.hibernating)
    self.assertEquals(False, desc.allow_single_hop_exits)
    self.assertEquals(False, desc.extra_info_cache)
    self.assertEquals("D225B728768D7EA4B5587C13A7A9D22EBBEE6E66", desc.extra_info_digest)
    self.assertEquals(["2"], desc.hidden_service_dir)
    self.assertEquals(expected_family, desc.family)
    self.assertEquals(153600, desc.average_bandwidth)
    self.assertEquals(256000, desc.burst_bandwidth)
    self.assertEquals(104590, desc.observed_bandwidth)
    self.assertEquals(stem.exit_policy.ExitPolicy("reject *:*"), desc.exit_policy)
    self.assertEquals(expected_onion_key, desc.onion_key)
    self.assertEquals(expected_signing_key, desc.signing_key)
    self.assertEquals(expected_signature, desc.signature)
    self.assertEquals([], desc.get_unrecognized_lines())
    self.assertEquals("2C7B27BEAB04B4E2459D89CA6D5CD1CC5F95A689", desc.digest())
  
  def test_old_descriptor(self):
    """
    Parses a relay server descriptor from 2005.
    """
    
    descriptor_path = test.integ.descriptor.get_resource("old_descriptor")
    
    descriptor_file = open(descriptor_path)
    descriptor_file.readline() # strip header
    descriptor_contents = descriptor_file.read()
    descriptor_file.close()
    
    desc = stem.descriptor.server_descriptor.RelayDescriptor(descriptor_contents)
    self.assertEquals("krypton", desc.nickname)
    self.assertEquals("3E2F63E2356F52318B536A12B6445373808A5D6C", desc.fingerprint)
    self.assertEquals("212.37.39.59", desc.address)
    self.assertEquals(8000, desc.or_port)
    self.assertEquals(None, desc.socks_port)
    self.assertEquals(None, desc.dir_port)
    self.assertEquals("Tor 0.1.0.14 on FreeBSD i386", desc.platform)
    self.assertEquals(stem.version.Version("0.1.0.14"), desc.tor_version)
    self.assertEquals("FreeBSD i386", desc.operating_system)
    self.assertEquals(64820, desc.uptime)
    self.assertEquals(datetime.datetime(2005, 12, 16, 18, 1, 3), desc.published)
    self.assertEquals(None, desc.contact)
    self.assertEquals(None, desc.link_protocols)
    self.assertEquals(None, desc.circuit_protocols)
    self.assertEquals(True, desc.hibernating)
    self.assertEquals(False, desc.allow_single_hop_exits)
    self.assertEquals(False, desc.extra_info_cache)
    self.assertEquals(None, desc.extra_info_digest)
    self.assertEquals(None, desc.hidden_service_dir)
    self.assertEquals([], desc.family)
    self.assertEquals(102400, desc.average_bandwidth)
    self.assertEquals(10485760, desc.burst_bandwidth)
    self.assertEquals(0, desc.observed_bandwidth)
    self.assertEquals(datetime.datetime(2005, 12, 16, 18, 0, 48), desc.read_history_end)
    self.assertEquals(900, desc.read_history_interval)
    self.assertEquals(datetime.datetime(2005, 12, 16, 18, 0, 48), desc.write_history_end)
    self.assertEquals(900, desc.write_history_interval)
    self.assertEquals([], desc.get_unrecognized_lines())
    
    # The read-history and write-history lines are pretty long so just checking
    # the initial contents for the line and parsed values.
    
    read_values_start = [20774, 489973, 510022, 511163, 20949]
    self.assertEquals(read_values_start, desc.read_history_values[:5])
    
    write_values_start = [81, 8848, 8927, 8927, 83, 8848, 8931, 8929, 81, 8846]
    self.assertEquals(write_values_start, desc.write_history_values[:10])
  
  def test_cached_descriptor(self):
    """
    Parses the cached descriptor file in our data directory, checking that it
    doesn't raise any validation issues and looking for unrecognized descriptor
    additions.
    """
    
    # lengthy test and uneffected by targets, so only run once
    if test.runner.only_run_once(self, "test_cached_descriptor"): return
    
    descriptor_path = test.runner.get_runner().get_test_dir("cached-descriptors")
    
    if not os.path.exists(descriptor_path):
      test.runner.skip(self, "(no cached descriptors)")
      return
    
    with open(descriptor_path) as descriptor_file:
      for desc in stem.descriptor.server_descriptor.parse_file(descriptor_file):
        # the following attributes should be deprecated, and not appear in the wild
        self.assertEquals(None, desc.read_history_end)
        self.assertEquals(None, desc.write_history_end)
        self.assertEquals(None, desc.eventdns)
        self.assertEquals(None, desc.socks_port)
        
        unrecognized_lines = desc.get_unrecognized_lines()
        
        if unrecognized_lines:
          # TODO: This isn't actually a problem, and rather than failing we
          # should alert the user about these entries at the end of the tests
          # (along with new events, getinfo options, and such). For now though
          # there doesn't seem to be anything in practice to trigger this so
          # failing to get our attention if it does.
          
          self.fail("Unrecognized descriptor content: %s" % unrecognized_lines)
  
  def test_non_ascii_descriptor(self):
    """
    Parses a descriptor with non-ascii content.
    """
    
    descriptor_path = test.integ.descriptor.get_resource("non-ascii_descriptor")
    
    descriptor_file = open(descriptor_path)
    descriptor_file.readline() # strip header
    descriptor_contents = descriptor_file.read()
    descriptor_file.close()
    
    expected_contact = "2048R/F171EC1F Johan Bl\xc3\xa5b\xc3\xa4ck \xe3\x81\x93\xe3\x82\x93\xe3\x81\xab\xe3\x81\xa1\xe3\x81\xaf"
    
    desc = stem.descriptor.server_descriptor.RelayDescriptor(descriptor_contents)
    self.assertEquals("torrelay389752132", desc.nickname)
    self.assertEquals("5D47E91A1F7421A4E3255F4D04E534E9A21407BB", desc.fingerprint)
    self.assertEquals("130.243.230.116", desc.address)
    self.assertEquals(9001, desc.or_port)
    self.assertEquals(None, desc.socks_port)
    self.assertEquals(None, desc.dir_port)
    self.assertEquals("Tor 0.2.2.35 (git-4f42b0a93422f70e) on Linux x86_64", desc.platform)
    self.assertEquals(stem.version.Version("0.2.2.35"), desc.tor_version)
    self.assertEquals("Linux x86_64", desc.operating_system)
    self.assertEquals(3103848, desc.uptime)
    self.assertEquals(datetime.datetime(2012, 3, 21, 16, 28, 14), desc.published)
    self.assertEquals(expected_contact, desc.contact)
    self.assertEquals(["1", "2"], desc.link_protocols)
    self.assertEquals(["1"], desc.circuit_protocols)
    self.assertEquals(False, desc.hibernating)
    self.assertEquals(False, desc.allow_single_hop_exits)
    self.assertEquals(False, desc.extra_info_cache)
    self.assertEquals("51E9FD0DA7C235D8C0250BAFB6E1ABB5F1EF9F04", desc.extra_info_digest)
    self.assertEquals(["2"], desc.hidden_service_dir)
    self.assertEquals([], desc.family)
    self.assertEquals(81920, desc.average_bandwidth)
    self.assertEquals(102400, desc.burst_bandwidth)
    self.assertEquals(84275, desc.observed_bandwidth)
    self.assertEquals(stem.exit_policy.ExitPolicy("reject *:*"), desc.exit_policy)
    self.assertEquals([], desc.get_unrecognized_lines())
  
  def test_cr_in_contact_line(self):
    """
    Parses a descriptor with a huge contact line containing anomalous carriage
    returns ('\r' entries).
    """
    
    descriptor_path = test.integ.descriptor.get_resource("cr_in_contact_line")
    
    descriptor_file = open(descriptor_path)
    descriptor_file.readline() # strip header
    descriptor_contents = descriptor_file.read()
    descriptor_file.close()
    
    desc = stem.descriptor.server_descriptor.RelayDescriptor(descriptor_contents)
    
    self.assertEquals("pogonip", desc.nickname)
    self.assertEquals("6DABD62BC65D4E6FE620293157FC76968DAB9C9B", desc.fingerprint)
    self.assertEquals("75.5.248.48", desc.address)
    
    # the contact info block is huge so just checking the start and end,
    # including some of the embedded carriage returns
    
    contact_start = "jie1 at pacbell dot net -----BEGIN PGP PUBLIC KEY BLOCK-----\rVersion:"
    contact_end = "YFRk3NhCY=\r=Xaw3\r-----END PGP PUBLIC KEY BLOCK-----"
    
    self.assertTrue(desc.contact.startswith(contact_start))
    self.assertTrue(desc.contact.endswith(contact_end))
  
  def test_negative_uptime(self):
    """
    Parses a descriptor where we are tolerant of a negative uptime, and another
    where we shouldn't be.
    """
    
    descriptor_path = test.integ.descriptor.get_resource("negative_uptime")
    
    descriptor_file = open(descriptor_path)
    descriptor_file.readline() # strip header
    descriptor_contents = descriptor_file.read()
    descriptor_file.close()
    
    desc = stem.descriptor.server_descriptor.RelayDescriptor(descriptor_contents)
    
    self.assertEquals("TipTor", desc.nickname)
    self.assertEquals("137962D4931DBF08A24E843288B8A155D6D2AEDD", desc.fingerprint)
    self.assertEquals("62.99.247.83", desc.address)
    
    # modify the relay version so it's after when the negative uptime bug
    # should appear
    
    descriptor_contents = descriptor_contents.replace("Tor 0.1.1.25", "Tor 0.1.2.7")
    self.assertRaises(ValueError, stem.descriptor.server_descriptor.RelayDescriptor, descriptor_contents)
  
  def test_bridge_descriptor(self):
    """
    Parses a bridge descriptor.
    """
    
    descriptor_path = test.integ.descriptor.get_resource("bridge_descriptor")
    
    descriptor_file = open(descriptor_path)
    descriptor_file.readline() # strip header
    descriptor_contents = descriptor_file.read()
    descriptor_file.close()
    
    expected_family = [
      "$CE396C72A3D0880F74C064FEA79D68C15BD380B9",
      "$AB8B00C00B1347BA80A88E548FAC9EDF701D7D0E",
      "$8C8A470D7C23151665A7B84E75E89FCC205A3304",
    ]
    
    desc = stem.descriptor.server_descriptor.BridgeDescriptor(descriptor_contents)
    self.assertEquals("Unnamed", desc.nickname)
    self.assertEquals("AE54E28ED069CDF45F3009F963EE3B3D6FA26A2E", desc.fingerprint)
    self.assertEquals("10.45.227.253", desc.address)
    self.assertEquals(9001, desc.or_port)
    self.assertEquals(None, desc.socks_port)
    self.assertEquals(None, desc.dir_port)
    self.assertEquals("Tor 0.2.3.12-alpha (git-800942b4176ca31c) on Linux x86_64", desc.platform)
    self.assertEquals(stem.version.Version("0.2.3.12-alpha"), desc.tor_version)
    self.assertEquals("Linux x86_64", desc.operating_system)
    self.assertEquals(186, desc.uptime)
    self.assertEquals(datetime.datetime(2012, 3, 22, 17, 34, 38), desc.published)
    self.assertEquals("somebody", desc.contact)
    self.assertEquals(["1", "2"], desc.link_protocols)
    self.assertEquals(["1"], desc.circuit_protocols)
    self.assertEquals(False, desc.hibernating)
    self.assertEquals(False, desc.allow_single_hop_exits)
    self.assertEquals(False, desc.extra_info_cache)
    self.assertEquals("134F81F7A0D270B85FCD481DD10CEA34BA7B15C9", desc.extra_info_digest)
    self.assertEquals(["2"], desc.hidden_service_dir)
    self.assertEquals(expected_family, desc.family)
    self.assertEquals(409600, desc.average_bandwidth)
    self.assertEquals(819200, desc.burst_bandwidth)
    self.assertEquals(5120, desc.observed_bandwidth)
    self.assertEquals(stem.exit_policy.ExitPolicy("reject *:*"), desc.exit_policy)
    self.assertEquals("006FD96BA35E7785A6A3B8B75FE2E2435A13BDB4", desc.digest())
    self.assertEquals([], desc.get_unrecognized_lines())

