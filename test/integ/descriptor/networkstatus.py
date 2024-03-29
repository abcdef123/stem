"""
Integration tests for stem.descriptor.networkstatus.
"""

from __future__ import with_statement

import datetime
import os
import resource
import unittest

import stem.descriptor
import stem.descriptor.networkstatus
import stem.version
import test.integ.descriptor

class TestNetworkStatus(unittest.TestCase):
  def test_cached_consensus(self):
    """
    Parses the cached-consensus file in our data directory.
    """
    
    # lengthy test and uneffected by targets, so only run once
    if test.runner.only_run_once(self, "test_cached_consensus"): return
    
    consensus_path = test.runner.get_runner().get_test_dir("cached-consensus")
    
    if not os.path.exists(consensus_path):
      test.runner.skip(self, "(no cached-consensus)")
      return
    elif stem.util.system.is_windows():
      # Unable to check memory usage on windows, so can't prevent hanging the
      # system if things go bad.
      
      test.runner.skip(self, "(unavailable on windows)")
      return
    
    count = 0
    with open(consensus_path) as descriptor_file:
      for router in stem.descriptor.networkstatus.parse_file(descriptor_file):
        count += 1
        
        # We should have constant memory usage. Fail if we're using over 200 MB.
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 200000:
          self.fail()
        
        # check if there's any unknown flags
        # TODO: this should be a 'new capability' check later rather than
        # failing the tests
        for flag in router.flags:
          if not flag in stem.descriptor.Flag:
            raise ValueError("Unrecognized flag type: %s, found on relay %s (%s)" % (flag, router.fingerprint, router.nickname))
        
        unrecognized_lines = router.get_unrecognized_lines()
        
        if unrecognized_lines:
          self.fail("Unrecognized descriptor content: %s" % unrecognized_lines)
    
    # Sanity test that there's at least a hundred relays. If that's not the
    # case then this probably isn't a real, complete tor consensus.
    
    self.assertTrue(count > 100)
  
  def test_cached_microdesc_consensus(self):
    """
    Parses the cached-microdesc-consensus file in our data directory.
    """
    
    # lengthy test and uneffected by targets, so only run once
    if test.runner.only_run_once(self, "test_cached_microdesc_consensus"): return
    
    consensus_path = test.runner.get_runner().get_test_dir("cached-microdesc-consensus")
    
    if not os.path.exists(consensus_path):
      test.runner.skip(self, "(no cached-microdesc-consensus)")
      return
    elif stem.util.system.is_windows():
      test.runner.skip(self, "(unavailable on windows)")
      return
    
    count = 0
    with open(consensus_path) as descriptor_file:
      for router in stem.descriptor.networkstatus.parse_file(descriptor_file, is_microdescriptor = True):
        count += 1
        
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 200000:
          self.fail()
        
        # check if there's any unknown flags
        # TODO: this should be a 'new capability' check later rather than
        # failing the tests
        for flag in router.flags:
          if not flag in stem.descriptor.Flag:
            raise ValueError("Unrecognized flag type: %s, found on microdescriptor relay %s (%s)" % (flag, router.fingerprint, router.nickname))
        
        unrecognized_lines = router.get_unrecognized_lines()
        
        if unrecognized_lines:
          self.fail("Unrecognized descriptor content: %s" % unrecognized_lines)
    
    self.assertTrue(count > 100)
  
  def test_metrics_consensus(self):
    """
    Checks if consensus documents from Metrics are parsed properly.
    """
    
    consensus_path = test.integ.descriptor.get_resource("metrics_consensus")
    
    with open(consensus_path) as descriptor_file:
      descriptors = stem.descriptor.parse_file(consensus_path, descriptor_file)
      
      router = next(descriptors)
      self.assertEquals("sumkledi", router.nickname)
      self.assertEquals("0013D22389CD50D0B784A3E4061CB31E8CE8CEB5", router.fingerprint)
      self.assertEquals("8mCr8Sl7RF4ENU4jb0FZFA/3do8", router.digest)
      self.assertEquals(datetime.datetime(2012, 7, 12, 4, 1, 55), router.published)
      self.assertEquals("178.218.213.229", router.address)
      self.assertEquals(80, router.or_port)
      self.assertEquals(None, router.dir_port)
  
  def test_consensus_v3(self):
    """
    Checks that version 3 consensus documents are properly parsed.
    """
    
    # the document's expected client and server versions are the same
    expected_versions = [stem.version.Version(v) for v in (
      "0.2.2.35",         "0.2.2.36",         "0.2.2.37",         "0.2.3.10-alpha",
      "0.2.3.11-alpha",   "0.2.3.12-alpha",   "0.2.3.13-alpha",   "0.2.3.14-alpha",
      "0.2.3.15-alpha",   "0.2.3.16-alpha",   "0.2.3.17-beta",    "0.2.3.18-rc",
      "0.2.3.19-rc",
    )]
    
    expected_flags = set(["Authority", "BadExit", "Exit", "Fast", "Guard", "HSDir",
      "Named", "Running", "Stable", "Unnamed", "V2Dir", "Valid"])
    
    expected_bandwidth_weights = {
      "Wbd": 3335, "Wbe": 0, "Wbg": 3536, "Wbm": 10000, "Wdb": 10000,
      "Web": 10000, "Wed": 3329, "Wee": 10000, "Weg": 3329, "Wem": 10000,
      "Wgb": 10000, "Wgd": 3335, "Wgg": 6464, "Wgm": 6464, "Wmb": 10000,
      "Wmd": 3335, "Wme": 0, "Wmg": 3536, "Wmm": 10000
    }
    
    expected_signature = """-----BEGIN SIGNATURE-----
HFXB4497LzESysYJ/4jJY83E5vLjhv+igIxD9LU6lf6ftkGeF+lNmIAIEKaMts8H
mfWcW0b+jsrXcJoCxV5IrwCDF3u1aC3diwZY6yiG186pwWbOwE41188XI2DeYPwE
I/TJmV928na7RLZe2mGHCAW3VQOvV+QkCfj05VZ8CsY=
-----END SIGNATURE-----"""
    
    consensus_path = test.integ.descriptor.get_resource("cached-consensus")
    
    with open(consensus_path) as descriptor_file:
      document = stem.descriptor.networkstatus.NetworkStatusDocumentV3(descriptor_file.read(), default_params = False)
      
      self.assertEquals(3, document.version)
      self.assertEquals(None, document.version_flavor)
      self.assertEquals(True, document.is_consensus)
      self.assertEquals(False, document.is_vote)
      self.assertEquals(False, document.is_microdescriptor)
      self.assertEquals(datetime.datetime(2012, 7, 12, 10, 0, 0), document.valid_after)
      self.assertEquals(datetime.datetime(2012, 7, 12, 11, 0, 0), document.fresh_until)
      self.assertEquals(datetime.datetime(2012, 7, 12, 13, 0, 0), document.valid_until)
      self.assertEquals(300, document.vote_delay)
      self.assertEquals(300, document.dist_delay)
      self.assertEquals(expected_versions, document.client_versions)
      self.assertEquals(expected_versions, document.server_versions)
      self.assertEquals(expected_flags, set(document.known_flags))
      self.assertEquals({"CircuitPriorityHalflifeMsec": 30000, "bwauthpid": 1}, document.params)
      
      self.assertEquals(12, document.consensus_method)
      self.assertEquals(expected_bandwidth_weights, document.bandwidth_weights)
      self.assertEquals([], document.consensus_methods)
      self.assertEquals(None, document.published)
      self.assertEquals([], document.get_unrecognized_lines())
      
      router = document.routers[0]
      self.assertEquals("sumkledi", router.nickname)
      self.assertEquals("0013D22389CD50D0B784A3E4061CB31E8CE8CEB5", router.fingerprint)
      self.assertEquals("8mCr8Sl7RF4ENU4jb0FZFA/3do8", router.digest)
      self.assertEquals(datetime.datetime(2012, 7, 12, 4, 1, 55), router.published)
      self.assertEquals("178.218.213.229", router.address)
      self.assertEquals(80, router.or_port)
      self.assertEquals(None, router.dir_port)
      self.assertEquals(set(["Exit", "Fast", "Named", "Running", "Valid"]), set(router.flags))
      
      authority = document.directory_authorities[0]
      self.assertEquals(8, len(document.directory_authorities))
      self.assertEquals("tor26", authority.nickname)
      self.assertEquals("14C131DFC5C6F93646BE72FA1401C02A8DF2E8B4", authority.fingerprint)
      self.assertEquals("86.59.21.38", authority.hostname)
      self.assertEquals("86.59.21.38", authority.address)
      self.assertEquals(80, authority.dir_port)
      self.assertEquals(443, authority.or_port)
      self.assertEquals("Peter Palfrader", authority.contact)
      self.assertEquals("0B6D1E9A300B895AA2D0B427F92917B6995C3C1C", authority.vote_digest)
      self.assertEquals(None, authority.legacy_dir_key)
      self.assertEquals(None, authority.key_certificate)
      
      signature = document.signatures[0]
      self.assertEquals(8, len(document.signatures))
      self.assertEquals("sha1", signature.method)
      self.assertEquals("14C131DFC5C6F93646BE72FA1401C02A8DF2E8B4", signature.identity)
      self.assertEquals("BF112F1C6D5543CFD0A32215ACABD4197B5279AD", signature.key_digest)
      self.assertEquals(expected_signature, signature.signature)
  
  def test_consensus_v2(self):
    """
    Checks that version 2 consensus documents are properly parsed.
    """
    
    expected_signing_key = """-----BEGIN RSA PUBLIC KEY-----
MIGJAoGBAOcrht/y5rkaahfX7sMe2qnpqoPibsjTSJaDvsUtaNP/Bq0MgNDGOR48
rtwfqTRff275Edkp/UYw3G3vSgKCJr76/bqOHCmkiZrnPV1zxNfrK18gNw2Cxre0
nTA+fD8JQqpPtb8b0SnG9kwy75eS//sRu7TErie2PzGMxrf9LH0LAgMBAAE=
-----END RSA PUBLIC KEY-----"""
    
    expected_signature = """-----BEGIN SIGNATURE-----
2nXCxVje3wzn6HrIFRNMc0nc48AhMVpHZyPwRKGXkuYfTQG55uvwQDaFgJHud4RT
27QhWltau3K1evhnzhKcpbTXwkVv1TBYJSzL6rEeAn8cQ7ZiCyqf4EJCaNcem3d2
TpQQk3nNQF8z6UIvdlvP+DnJV4izWVkQEZgUZgIVM0E=
-----END SIGNATURE-----"""
    
    consensus_path = test.integ.descriptor.get_resource("cached-consensus-v2")
    
    with open(consensus_path) as descriptor_file:
      descriptor_file.readline() # strip header
      document = stem.descriptor.networkstatus.NetworkStatusDocumentV2(descriptor_file.read())
      
      self.assertEquals(2, document.version)
      self.assertEquals("18.244.0.114", document.hostname)
      self.assertEquals("18.244.0.114", document.address)
      self.assertEquals(80, document.dir_port)
      self.assertEquals("719BE45DE224B607C53707D0E2143E2D423E74CF", document.fingerprint)
      self.assertEquals("arma at mit dot edu", document.contact)
      self.assertEquals(expected_signing_key, document.signing_key)
      
      self.assertEquals(67, len(document.client_versions))
      self.assertEquals("0.0.9rc2", document.client_versions[0])
      self.assertEquals("0.1.1.10-alpha-cvs", document.client_versions[-1])
      
      self.assertEquals(67, len(document.server_versions))
      self.assertEquals("0.0.9rc2", document.server_versions[0])
      self.assertEquals("0.1.1.10-alpha-cvs", document.server_versions[-1])
      
      self.assertEquals(datetime.datetime(2005, 12, 16, 0, 13, 46), document.published)
      self.assertEquals(["Names", "Versions"], document.options)
      self.assertEquals("moria2", document.signing_authority)
      self.assertEquals(expected_signature, document.signature)
      self.assertEquals([], document.get_unrecognized_lines())
      
      self.assertEqual(3, len(document.routers))
      
      router1 = document.routers[0]
      self.assertEquals("moria2", router1.nickname)
      self.assertEquals("719BE45DE224B607C53707D0E2143E2D423E74CF", router1.fingerprint)
      self.assertEquals("t/Pwl1uHiJ3RKF/Vehsbthf2VDI", router1.digest)
      self.assertEquals(datetime.datetime(2005, 12, 15, 6, 57, 18), router1.published)
      self.assertEquals("18.244.0.114", router1.address)
      self.assertEquals(443, router1.or_port)
      self.assertEquals(80, router1.dir_port)
      self.assertEquals(set(["Authority", "Fast", "Named", "Running", "Valid", "V2Dir"]), set(router1.flags))
      
      router2 = document.routers[1]
      self.assertEquals("stnv", router2.nickname)
      self.assertEquals("0928BA467056C4A689FEE4EF5D71482B6289C3D5", router2.fingerprint)
      self.assertEquals("ItGn7UGZvaftbEFu7NdpwY4fKlo", router2.digest)
      self.assertEquals(datetime.datetime(2005, 12, 15, 16, 24, 42), router2.published)
      self.assertEquals("84.16.236.173", router2.address)
      self.assertEquals(9001, router2.or_port)
      self.assertEquals(None, router2.dir_port)
      self.assertEquals(set(["Named", "Valid"]), set(router2.flags))
      
      router3 = document.routers[2]
      self.assertEquals("nggrplz", router3.nickname)
      self.assertEquals("09E8582FF0E6F85E2B8E41C0DC0B9C9DC46E6968", router3.fingerprint)
      self.assertEquals("swLCsByU85jj7ziTlSawZR+CTdY", router3.digest)
      self.assertEquals(datetime.datetime(2005, 12, 15, 23, 25, 50), router3.published)
      self.assertEquals("194.109.109.109", router3.address)
      self.assertEquals(9001, router3.or_port)
      self.assertEquals(None, router3.dir_port)
      self.assertEquals(set(["Fast", "Stable", "Running", "Valid"]), set(router3.flags))
  
  def test_metrics_vote(self):
    """
    Checks if vote documents from Metrics are parsed properly.
    """
    
    vote_path = test.integ.descriptor.get_resource("metrics_vote")
    
    with open(vote_path) as descriptor_file:
      descriptors = stem.descriptor.parse_file(vote_path, descriptor_file)
      
      router = next(descriptors)
      self.assertEquals("sumkledi", router.nickname)
      self.assertEquals("0013D22389CD50D0B784A3E4061CB31E8CE8CEB5", router.fingerprint)
      self.assertEquals("B5n4BiALAF8B5AqafxohyYiuj7E", router.digest)
      self.assertEquals(datetime.datetime(2012, 7, 11, 4, 22, 53), router.published)
      self.assertEquals("178.218.213.229", router.address)
      self.assertEquals(80, router.or_port)
      self.assertEquals(None, router.dir_port)
  
  def test_vote(self):
    """
    Checks that vote documents are properly parsed.
    """
    
    expected_flags = set(["Authority", "BadExit", "Exit", "Fast", "Guard", "HSDir",
      "Running", "Stable", "V2Dir", "Valid"])
    
    expected_identity_key = """-----BEGIN RSA PUBLIC KEY-----
MIIBigKCAYEA6uSmsoxj2MiJ3qyZq0qYXlRoG8o82SNqg+22m+t1c7MlQOZWPJYn
XeMcBCt8xrTeIt2ZI+Q/Kt2QJSeD9WZRevTKk/kn5Tg2+xXPogalUU47y5tUohGz
+Q8+CxtRSXpDxBHL2P8rLHvGrI69wbNHGoQkce/7gJy9vw5Ie2qzbyXk1NG6V8Fb
pr6A885vHo6TbhUnolz2Wqt/kN+UorjLkN2H3fV+iGcQFv42SyHYGDLa0WwL3PJJ
r/veu36S3VaHBrfhutfioi+d3d4Ya0bKwiWi5Lm2CHuuRTgMpHLU9vlci8Hunuxq
HsULe2oMsr4VEic7sW5SPC5Obpx6hStHdNv1GxoSEm3/vIuPM8pINpU5ZYAyH9yO
Ef22ZHeiVMMKmpV9TtFyiFqvlI6GpQn3mNbsQqF1y3XCA3Q4vlRAkpgJVUSvTxFP
2bNDobOyVCpCM/rwxU1+RCNY5MFJ/+oktUY+0ydvTen3gFdZdgNqCYjKPLfBNm9m
RGL7jZunMUNvAgMBAAE=
-----END RSA PUBLIC KEY-----"""
    
    expected_signing_key = """-----BEGIN RSA PUBLIC KEY-----
MIGJAoGBAJ5itcJRYNEM3Qf1OVWLRkwjqf84oXPc2ZusaJ5zOe7TVvBMra9GNyc0
NM9y6zVkHCAePAjr4KbW/8P1olA6FUE2LV9bozaU1jFf6K8B2OELKs5FUEW+n+ic
GM0x6MhngyXonWOcKt5Gj+mAu5lrno9tpNbPkz2Utr/Pi0nsDhWlAgMBAAE=
-----END RSA PUBLIC KEY-----"""
    
    expected_key_crosscert = """-----BEGIN ID SIGNATURE-----
RHYImGTwg36wmEdAn7qaRg2sAfql7ZCtPIL/O3lU5OIdXXp0tNn/K00Bamqohjk+
Tz4FKsKXGDlbGv67PQcZPOK6NF0GRkNh4pk89prrDO4XwtEn7rkHHdBH6/qQ7IRG
GdDZHtZ1a69oFZvPWD3hUaB50xeIe7GoKdKIfdNNJ+8=
-----END ID SIGNATURE-----"""
    
    expected_key_certification = """-----BEGIN SIGNATURE-----
fasWOGyUZ3iMCYpDfJ+0JcMiTH25sXPWzvlHorEOyOMbaMqRYpZU4GHzt1jLgdl6
AAoR6KdamsLg5VE8xzst48a4UFuzHFlklZ5O8om2rcvDd5DhSnWWYZnYJecqB+bo
dNisPmaIVSAWb29U8BpNRj4GMC9KAgGYUj8aE/KtutAeEekFfFEHTfWZ2fFp4j3m
9rY8FWraqyiF+Emq1T8pAAgMQ+79R3oZxq0TXS42Z4Anhms735ccauKhI3pDKjbl
tD5vAzIHOyjAOXj7a6jY/GrnaBNuJ4qe/4Hf9UmzK/jKKwG95BPJtPTT4LoFwEB0
KG2OUeQUNoCck4nDpsZwFqPlrWCHcHfTV2iDYFV1HQWDTtZz/qf+GtB8NXsq+I1w
brADmvReM2BD6p/13h0QURCI5hq7ZYlIKcKrBa0jn1d9cduULl7vgKsRCJDls/ID
emBZ6pUxMpBmV0v+PrA3v9w4DlE7GHAq61FF/zju2kpqj6MInbEvI/E+e438sWsL
-----END SIGNATURE-----"""
    
    expected_signature = """-----BEGIN SIGNATURE-----
fskXN84wB3mXfo+yKGSt0AcDaaPuU3NwMR3ROxWgLN0KjAaVi2eV9PkPCsQkcgw3
JZ/1HL9sHyZfo6bwaC6YSM9PNiiY6L7rnGpS7UkHiFI+M96VCMorvjm5YPs3FioJ
DnN5aFtYKiTc19qIC7Nmo+afPdDEf0MlJvEOP5EWl3w=
-----END SIGNATURE-----"""
    
    vote_path = test.integ.descriptor.get_resource("vote")
    
    with open(vote_path) as descriptor_file:
      document = stem.descriptor.networkstatus.NetworkStatusDocumentV3(descriptor_file.read(), default_params = False)
      
      self.assertEquals(3, document.version)
      self.assertEquals(None, document.version_flavor)
      self.assertEquals(False, document.is_consensus)
      self.assertEquals(True, document.is_vote)
      self.assertEquals(False, document.is_microdescriptor)
      self.assertEquals(datetime.datetime(2012, 7, 12, 0, 0, 0), document.valid_after)
      self.assertEquals(datetime.datetime(2012, 7, 12, 1, 0, 0), document.fresh_until)
      self.assertEquals(datetime.datetime(2012, 7, 12, 3, 0, 0), document.valid_until)
      self.assertEquals(300, document.vote_delay)
      self.assertEquals(300, document.dist_delay)
      self.assertEquals([], document.client_versions)
      self.assertEquals([], document.server_versions)
      self.assertEquals(expected_flags, set(document.known_flags))
      self.assertEquals({"CircuitPriorityHalflifeMsec": 30000, "bwauthpid": 1}, document.params)
      
      self.assertEquals(None, document.consensus_method)
      self.assertEquals({}, document.bandwidth_weights)
      self.assertEquals(range(1, 13), document.consensus_methods)
      self.assertEquals(datetime.datetime(2012, 7, 11, 23, 50, 1), document.published)
      self.assertEquals([], document.get_unrecognized_lines())
      
      router = document.routers[0]
      self.assertEquals("sumkledi", router.nickname)
      self.assertEquals("0013D22389CD50D0B784A3E4061CB31E8CE8CEB5", router.fingerprint)
      self.assertEquals("B5n4BiALAF8B5AqafxohyYiuj7E", router.digest)
      self.assertEquals(datetime.datetime(2012, 7, 11, 4, 22, 53), router.published)
      self.assertEquals("178.218.213.229", router.address)
      self.assertEquals(80, router.or_port)
      self.assertEquals(None, router.dir_port)
      
      authority = document.directory_authorities[0]
      self.assertEquals(1, len(document.directory_authorities))
      self.assertEquals("turtles", authority.nickname)
      self.assertEquals("27B6B5996C426270A5C95488AA5BCEB6BCC86956", authority.fingerprint)
      self.assertEquals("76.73.17.194", authority.hostname)
      self.assertEquals("76.73.17.194", authority.address)
      self.assertEquals(9030, authority.dir_port)
      self.assertEquals(9090, authority.or_port)
      self.assertEquals("Mike Perry <email>", authority.contact)
      self.assertEquals(None, authority.vote_digest)
      self.assertEquals(None, authority.legacy_dir_key)
      
      certificate = authority.key_certificate
      self.assertEquals(3, certificate.version)
      self.assertEquals(None, certificate.address)
      self.assertEquals(None, certificate.dir_port)
      self.assertEquals("27B6B5996C426270A5C95488AA5BCEB6BCC86956", certificate.fingerprint)
      self.assertEquals(expected_identity_key, certificate.identity_key)
      self.assertEquals(datetime.datetime(2011, 11, 28, 21, 51, 4), certificate.published)
      self.assertEquals(datetime.datetime(2012, 11, 28, 21, 51, 4), certificate.expires)
      self.assertEquals(expected_signing_key, certificate.signing_key)
      self.assertEquals(expected_key_crosscert, certificate.crosscert)
      self.assertEquals(expected_key_certification, certificate.certification)
      
      signature = document.signatures[0]
      self.assertEquals(1, len(document.signatures))
      self.assertEquals("sha1", signature.method)
      self.assertEquals("27B6B5996C426270A5C95488AA5BCEB6BCC86956", signature.identity)
      self.assertEquals("D5C30C15BB3F1DA27669C2D88439939E8F418FCF", signature.key_digest)
      self.assertEquals(expected_signature, signature.signature)

