"""
Unit tests for the stem.response.events classes.
"""

import datetime
import threading
import unittest

import stem.response
import stem.response.events
import stem.util.log

from stem import * # enums and exceptions
from test import mocking

# ADDRMAP event

ADDRMAP = '650 ADDRMAP www.atagar.com 75.119.206.243 "2012-11-19 00:50:13" \
EXPIRES="2012-11-19 08:50:13"'

ADDRMAP_ERROR_EVENT = '650 ADDRMAP www.atagar.com <error> "2012-11-19 00:50:13" \
error=yes EXPIRES="2012-11-19 08:50:13"'

ADDRMAP_BAD_1 = '650 ADDRMAP www.atagar.com 75.119.206.243 2012-11-19 00:50:13" \
EXPIRES="2012-11-19 08:50:13"'

ADDRMAP_BAD_2 = '650 ADDRMAP www.atagar.com 75.119.206.243 "2012-11-19 00:50:13 \
EXPIRES="2012-11-19 08:50:13"'

# BUILDTIMEOUT_SET event from tor 0.2.3.16.

BUILD_TIMEOUT_EVENT = "650 BUILDTIMEOUT_SET COMPUTED \
TOTAL_TIMES=124 \
TIMEOUT_MS=9019 \
XM=1375 \
ALPHA=0.855662 \
CUTOFF_QUANTILE=0.800000 \
TIMEOUT_RATE=0.137097 \
CLOSE_MS=21850 \
CLOSE_RATE=0.072581"

BUILD_TIMEOUT_EVENT_BAD_1 = "650 BUILDTIMEOUT_SET COMPUTED \
TOTAL_TIMES=one_twenty_four \
TIMEOUT_MS=9019 \
XM=1375 \
ALPHA=0.855662 \
CUTOFF_QUANTILE=0.800000 \
TIMEOUT_RATE=0.137097 \
CLOSE_MS=21850 \
CLOSE_RATE=0.072581"

BUILD_TIMEOUT_EVENT_BAD_2 = "650 BUILDTIMEOUT_SET COMPUTED \
TOTAL_TIMES=124 \
TIMEOUT_MS=9019 \
XM=1375 \
ALPHA=0.855662 \
CUTOFF_QUANTILE=zero_point_eight \
TIMEOUT_RATE=0.137097 \
CLOSE_MS=21850 \
CLOSE_RATE=0.072581"

# CIRC events from tor v0.2.3.16

CIRC_LAUNCHED = "650 CIRC 7 LAUNCHED \
BUILD_FLAGS=NEED_CAPACITY \
PURPOSE=GENERAL \
TIME_CREATED=2012-11-08T16:48:38.417238"

CIRC_LAUNCHED_BAD_1 = "650 CIRC 7 LAUNCHED \
BUILD_FLAGS=NEED_CAPACITY \
PURPOSE=GENERAL \
TIME_CREATED=20121108T164838417238"

CIRC_LAUNCHED_BAD_2 = "650 CIRC toolong8901234567 LAUNCHED \
BUILD_FLAGS=NEED_CAPACITY \
PURPOSE=GENERAL \
TIME_CREATED=2012-11-08T16:48:38.417238"

CIRC_EXTENDED = "650 CIRC 7 EXTENDED \
$999A226EBED397F331B612FE1E4CFAE5C1F201BA=piyaz \
BUILD_FLAGS=NEED_CAPACITY \
PURPOSE=GENERAL \
TIME_CREATED=2012-11-08T16:48:38.417238"

CIRC_FAILED = "650 CIRC 5 FAILED \
$E57A476CD4DFBD99B4EE52A100A58610AD6E80B9=ergebnisoffen \
BUILD_FLAGS=NEED_CAPACITY \
PURPOSE=GENERAL \
TIME_CREATED=2012-11-08T16:48:36.400959 \
REASON=DESTROYED \
REMOTE_REASON=OR_CONN_CLOSED"

# CIRC events from tor v0.2.1.30 without the VERBOSE_NAMES feature

CIRC_LAUNCHED_OLD = "650 CIRC 4 LAUNCHED"
CIRC_EXTENDED_OLD = "650 CIRC 1 EXTENDED \
$E57A476CD4DFBD99B4EE52A100A58610AD6E80B9,hamburgerphone"
CIRC_BUILT_OLD = "650 CIRC 1 BUILT \
$E57A476CD4DFBD99B4EE52A100A58610AD6E80B9,hamburgerphone,PrivacyRepublic14"

# CIRC_MINOR event from tor 0.2.3.16.

CIRC_MINOR_EVENT = "650 CIRC_MINOR 7 PURPOSE_CHANGED \
$67B2BDA4264D8A189D9270E28B1D30A262838243~europa1 \
BUILD_FLAGS=IS_INTERNAL,NEED_CAPACITY \
PURPOSE=MEASURE_TIMEOUT \
TIME_CREATED=2012-12-03T16:45:33.409602 \
OLD_PURPOSE=TESTING"

CIRC_MINOR_EVENT_BAD_1 = "650 CIRC_MINOR 7 PURPOSE_CHANGED \
$67B2BDA4264D8A189D9270E28B1D30A262838243~europa1 \
BUILD_FLAGS=IS_INTERNAL,NEED_CAPACITY \
PURPOSE=MEASURE_TIMEOUT \
TIME_CREATED=20121203T164533409602 \
OLD_PURPOSE=TESTING"

CIRC_MINOR_EVENT_BAD_2 = "650 CIRC_MINOR toolong8901234567 PURPOSE_CHANGED \
$67B2BDA4264D8A189D9270E28B1D30A262838243~europa1 \
BUILD_FLAGS=IS_INTERNAL,NEED_CAPACITY \
PURPOSE=MEASURE_TIMEOUT \
TIME_CREATED=2012-12-03T16:45:33.409602 \
OLD_PURPOSE=TESTING"

# CLIENTS_SEEN example from the spec

CLIENTS_SEEN_EVENT = '650 CLIENTS_SEEN \
TimeStarted="2008-12-25 23:50:43" \
CountrySummary=us=16,de=8,uk=8 \
IPVersions=v4=16,v6=40'

CLIENTS_SEEN_EVENT_BAD_1 = '650 CLIENTS_SEEN \
TimeStarted="2008-12-25 23:50:43" \
CountrySummary=us:16,de:8,uk:8 \
IPVersions=v4=16,v6=40'

CLIENTS_SEEN_EVENT_BAD_2 = '650 CLIENTS_SEEN \
TimeStarted="2008-12-25 23:50:43" \
CountrySummary=usa=16,unitedkingdom=8 \
IPVersions=v4=16,v6=40'

CLIENTS_SEEN_EVENT_BAD_3 = '650 CLIENTS_SEEN \
TimeStarted="2008-12-25 23:50:43" \
CountrySummary=us=16,de=8,uk=eight \
IPVersions=v4=16,v6=40'

CLIENTS_SEEN_EVENT_BAD_4 = '650 CLIENTS_SEEN \
TimeStarted="2008-12-25 23:50:43" \
CountrySummary=au=16,au=8,au=8 \
IPVersions=v4=16,v6=40'

CLIENTS_SEEN_EVENT_BAD_5 = '650 CLIENTS_SEEN \
TimeStarted="2008-12-25 23:50:43" \
CountrySummary=us=16,de=8,uk=8 \
IPVersions=v4:16,v6:40'

CLIENTS_SEEN_EVENT_BAD_6 = '650 CLIENTS_SEEN \
TimeStarted="2008-12-25 23:50:43" \
CountrySummary=us=16,de=8,uk=8 \
IPVersions=v4=sixteen,v6=40'

# CONF_CHANGED event from tor 0.2.3.16.

CONF_CHANGED_EVENT = """650-CONF_CHANGED
650-ExitNodes=caerSidi
650-ExitPolicy
650-MaxCircuitDirtiness=20
650 OK
"""

# GUARD events from tor v0.2.1.30.

GUARD_NEW = "650 GUARD ENTRY $36B5DBA788246E8369DBAF58577C6BC044A9A374 NEW"
GUARD_GOOD = "650 GUARD ENTRY $5D0034A368E0ABAF663D21847E1C9B6CFA09752A GOOD"
GUARD_BAD = "650 GUARD ENTRY $5D0034A368E0ABAF663D21847E1C9B6CFA09752A BAD"

# NEWCONSENSUS event from v0.2.1.30.

NEWCONSENSUS_EVENT = """650+NEWCONSENSUS
r Beaver /96bKo4soysolMgKn5Hex2nyFSY pAJH9dSBp/CG6sPhhVY/5bLaVPM 2012-12-02 22:02:45 77.223.43.54 9001 0
s Fast Named Running Stable Valid
r Unnamed /+fJRWjmIGNAL2C5rRZHq3R91tA 7AnpZjfdBpYzXnMNm+w1bTsFF6Y 2012-12-02 17:51:10 91.121.184.87 9001 0
s Fast Guard Running Stable Valid
.
650 OK
"""

# NEWDESC events. I've never actually seen multiple descriptors in an event,
# but the spec allows for it.

NEWDESC_SINGLE = "650 NEWDESC $B3FA3110CC6F42443F039220C134CBD2FC4F0493=Sakura"
NEWDESC_MULTIPLE = "650 NEWDESC $BE938957B2CA5F804B3AFC2C1EE6673170CDBBF8=Moonshine \
$B4BE08B22D4D2923EDC3970FD1B93D0448C6D8FF~Unnamed"

# NS event from tor v0.2.1.30.

NS_EVENT = """650+NS
r whnetz dbBxYcJriTTrcxsuy4PUZcMRwCA VStM7KAIH/mXXoGDUpoGB1OXufg 2012-12-02 21:03:56 141.70.120.13 9001 9030
s Fast HSDir Named Stable V2Dir Valid
.
650 OK
"""

# ORCONN events from starting tor 0.2.2.39 via TBB

ORCONN_CLOSED = "650 ORCONN $A1130635A0CDA6F60C276FBF6994EFBD4ECADAB1~tama CLOSED REASON=DONE"
ORCONN_CONNECTED = "650 ORCONN 127.0.0.1:9000 CONNECTED NCIRCS=20"
ORCONN_LAUNCHED = "650 ORCONN $7ED90E2833EE38A75795BA9237B0A4560E51E1A0=GreenDragon LAUNCHED"

ORCONN_BAD_1 = "650 ORCONN $7ED90E2833EE38A75795BA9237B0A4560E5=GreenD LAUNCHED"
ORCONN_BAD_2 = "650 ORCONN 127.0.0.1:001 CONNECTED"
ORCONN_BAD_3 = "650 ORCONN 127.0.0.1:9000 CONNECTED NCIRCS=too_many"

# STATUS_* events that I was able to easily trigger. Most came from starting
# TBB, then listening while it bootstrapped.

STATUS_GENERAL_CONSENSUS_ARRIVED = "650 STATUS_GENERAL NOTICE CONSENSUS_ARRIVED"

STATUS_CLIENT_ENOUGH_DIR_INFO = "650 STATUS_CLIENT NOTICE ENOUGH_DIR_INFO"
STATUS_CLIENT_CIRC_ESTABLISHED = "650 STATUS_CLIENT NOTICE CIRCUIT_ESTABLISHED"

STATUS_CLIENT_BOOTSTRAP_DESCRIPTORS = '650 STATUS_CLIENT NOTICE BOOTSTRAP \
PROGRESS=53 \
TAG=loading_descriptors \
SUMMARY="Loading relay descriptors"'

STATUS_CLIENT_BOOTSTRAP_STUCK = '650 STATUS_CLIENT WARN BOOTSTRAP \
PROGRESS=80 \
TAG=conn_or \
SUMMARY="Connecting to the Tor network" \
WARNING="Network is unreachable" \
REASON=NOROUTE \
COUNT=5 \
RECOMMENDATION=warn'

STATUS_CLIENT_BOOTSTRAP_CONNECTING = '650 STATUS_CLIENT NOTICE BOOTSTRAP \
PROGRESS=80 \
TAG=conn_or \
SUMMARY="Connecting to the Tor network"'

STATUS_CLIENT_BOOTSTRAP_FIRST_HANDSHAKE = '650 STATUS_CLIENT NOTICE BOOTSTRAP \
PROGRESS=85 \
TAG=handshake_or \
SUMMARY="Finishing handshake with first hop"'

STATUS_CLIENT_BOOTSTRAP_ESTABLISHED = '650 STATUS_CLIENT NOTICE BOOTSTRAP \
PROGRESS=90 \
TAG=circuit_create \
SUMMARY="Establishing a Tor circuit"'

STATUS_CLIENT_BOOTSTRAP_DONE = '650 STATUS_CLIENT NOTICE BOOTSTRAP \
PROGRESS=100 \
TAG=done \
SUMMARY="Done"'

STATUS_SERVER_CHECK_REACHABILITY = "650 STATUS_SERVER NOTICE CHECKING_REACHABILITY \
ORADDRESS=71.35.143.230:9050"

STATUS_SERVER_DNS_TIMEOUT = '650 STATUS_SERVER NOTICE NAMESERVER_STATUS \
NS=205.171.3.25 \
STATUS=DOWN \
ERR="request timed out."'

STATUS_SERVER_DNS_DOWN = "650 STATUS_SERVER WARN NAMESERVER_ALL_DOWN"

STATUS_SERVER_DNS_UP = "650 STATUS_SERVER NOTICE NAMESERVER_STATUS \
NS=205.171.3.25 \
STATUS=UP"

# unknown STATUS_* event type
STATUS_SPECIFIC_CONSENSUS_ARRIVED = "650 STATUS_SPECIFIC NOTICE CONSENSUS_ARRIVED"

# STREAM events from tor 0.2.3.16 for visiting the google front page

STREAM_NEW = "650 STREAM 18 NEW 0 \
encrypted.google.com:443 \
SOURCE_ADDR=127.0.0.1:47849 \
PURPOSE=USER"

STREAM_SENTCONNECT = "650 STREAM 18 SENTCONNECT 26 encrypted.google.com:443"
STREAM_REMAP = "650 STREAM 18 REMAP 26 74.125.227.129:443 SOURCE=EXIT"
STREAM_SUCCEEDED = "650 STREAM 18 SUCCEEDED 26 74.125.227.129:443"
STREAM_CLOSED_RESET = "650 STREAM 21 CLOSED 26 74.125.227.129:443 REASON=CONNRESET"
STREAM_CLOSED_DONE = "650 STREAM 25 CLOSED 26 199.7.52.72:80 REASON=DONE"

STREAM_DIR_FETCH = "650 STREAM 14 NEW 0 \
176.28.51.238.$649F2D0ACF418F7CFC6539AB2257EB2D5297BAFA.exit:443 \
SOURCE_ADDR=(Tor_internal):0 PURPOSE=DIR_FETCH"

STREAM_DNS_REQUEST = "650 STREAM 1113 NEW 0 www.google.com:0 \
SOURCE_ADDR=127.0.0.1:15297 \
PURPOSE=DNS_REQUEST"

STREAM_SENTCONNECT_BAD_1 = "650 STREAM 18 SENTCONNECT 26"
STREAM_SENTCONNECT_BAD_2 = "650 STREAM 18 SENTCONNECT 26 encrypted.google.com"
STREAM_SENTCONNECT_BAD_3 = "650 STREAM 18 SENTCONNECT 26 encrypted.google.com:https"

STREAM_DNS_REQUEST_BAD_1 = "650 STREAM 1113 NEW 0 www.google.com:0 \
SOURCE_ADDR=127.0.0.1 \
PURPOSE=DNS_REQUEST"

STREAM_DNS_REQUEST_BAD_2 = "650 STREAM 1113 NEW 0 www.google.com:0 \
SOURCE_ADDR=127.0.0.1:dns \
PURPOSE=DNS_REQUEST"


def _get_event(content):
  controller_event = mocking.get_message(content)
  stem.response.convert("EVENT", controller_event, arrived_at = 25)
  return controller_event

class TestEvents(unittest.TestCase):
  def test_example(self):
    """
    Exercises the add_event_listener() pydoc example, but without the sleep().
    """
    
    import time
    from stem.control import Controller, EventType
    
    def print_bw(event):
      msg = "sent: %i, received: %i" % (event.written, event.read)
      self.assertEqual("sent: 25, received: 15", msg)
    
    def event_sender():
      for index in xrange(3):
        print_bw(_get_event("650 BW 15 25"))
        time.sleep(0.05)
    
    controller = mocking.get_object(Controller, {
      'authenticate': mocking.no_op(),
      'add_event_listener': mocking.no_op(),
    })
    
    controller.authenticate()
    controller.add_event_listener(print_bw, EventType.BW)
    
    events_thread = threading.Thread(target = event_sender)
    events_thread.start()
    time.sleep(0.2)
    events_thread.join()
  
  def test_event(self):
    # synthetic, contrived message construction to reach the blank event check
    self.assertRaises(ProtocolError, stem.response.convert, "EVENT", stem.response.ControlMessage([('', '', '')], ''), arrived_at = 25)
    
    # Event._parse_message() on an unknown event type
    event = _get_event('650 NONE SOLID "NON SENSE" condition=MEH quoted="1 2 3"')
    self.assertEqual("NONE", event.type)
    self.assertEqual(["SOLID", '"NON', 'SENSE"'], event.positional_args)
    self.assertEqual({"condition":"MEH", "quoted":"1 2 3"}, event.keyword_args)
  
  def test_log_events(self):
    event = _get_event("650 DEBUG connection_edge_process_relay_cell(): Got an extended cell! Yay.")
    
    self.assertTrue(isinstance(event, stem.response.events.LogEvent))
    self.assertEqual("DEBUG", event.runlevel)
    self.assertEqual("connection_edge_process_relay_cell(): Got an extended cell! Yay.", event.message)
    
    event = _get_event("650 INFO circuit_finish_handshake(): Finished building circuit hop:")
    
    self.assertTrue(isinstance(event, stem.response.events.LogEvent))
    self.assertEqual("INFO", event.runlevel)
    self.assertEqual("circuit_finish_handshake(): Finished building circuit hop:", event.message)
    
    event = _get_event("650+WARN\na multi-line\nwarning message\n.\n650 OK\n")
    
    self.assertTrue(isinstance(event, stem.response.events.LogEvent))
    self.assertEqual("WARN", event.runlevel)
    self.assertEqual("a multi-line\nwarning message", event.message)
  
  def test_addrmap_event(self):
    event = _get_event(ADDRMAP)
    
    self.assertTrue(isinstance(event, stem.response.events.AddrMapEvent))
    self.assertEqual(ADDRMAP.lstrip("650 "), str(event))
    self.assertEqual("www.atagar.com", event.hostname)
    self.assertEqual("75.119.206.243", event.destination)
    self.assertEqual(datetime.datetime(2012, 11, 19, 0, 50, 13), event.expiry)
    self.assertEqual(None, event.error)
    self.assertEqual(datetime.datetime(2012, 11, 19, 8, 50, 13), event.utc_expiry)
    
    event = _get_event(ADDRMAP_ERROR_EVENT)
    
    self.assertTrue(isinstance(event, stem.response.events.AddrMapEvent))
    self.assertEqual(ADDRMAP_ERROR_EVENT.lstrip("650 "), str(event))
    self.assertEqual("www.atagar.com", event.hostname)
    self.assertEqual(None, event.destination)
    self.assertEqual(datetime.datetime(2012, 11, 19, 0, 50, 13), event.expiry)
    self.assertEqual("yes", event.error)
    self.assertEqual(datetime.datetime(2012, 11, 19, 8, 50, 13), event.utc_expiry)
    
    # malformed content where quotes are missing
    self.assertRaises(ProtocolError, _get_event, ADDRMAP_BAD_1)
    self.assertRaises(ProtocolError, _get_event, ADDRMAP_BAD_2)
  
  def test_authdir_newdesc_event(self):
    # TODO: awaiting test data - https://trac.torproject.org/7534
    
    event = _get_event("650+AUTHDIR_NEWDESCS\nAction\nMessage\nDescriptor\n.\n650 OK\n")
    
    self.assertTrue(isinstance(event, stem.response.events.AuthDirNewDescEvent))
    self.assertEqual([], event.positional_args)
    self.assertEqual({}, event.keyword_args)
  
  def test_build_timeout_set_event(self):
    event = _get_event(BUILD_TIMEOUT_EVENT)
    
    self.assertTrue(isinstance(event, stem.response.events.BuildTimeoutSetEvent))
    self.assertEqual(BUILD_TIMEOUT_EVENT.lstrip("650 "), str(event))
    self.assertEqual(TimeoutSetType.COMPUTED, event.set_type)
    self.assertEqual(124, event.total_times)
    self.assertEqual(9019, event.timeout)
    self.assertEqual(1375, event.xm)
    self.assertEqual(0.855662, event.alpha)
    self.assertEqual(0.8, event.quantile)
    self.assertEqual(0.137097, event.timeout_rate)
    self.assertEqual(21850, event.close_timeout)
    self.assertEqual(0.072581, event.close_rate)
    
    # malformed content where we get non-numeric values
    self.assertRaises(ProtocolError, _get_event, BUILD_TIMEOUT_EVENT_BAD_1)
    self.assertRaises(ProtocolError, _get_event, BUILD_TIMEOUT_EVENT_BAD_2)
  
  def test_bw_event(self):
    event = _get_event("650 BW 15 25")
    
    self.assertTrue(isinstance(event, stem.response.events.BandwidthEvent))
    self.assertEqual(15, event.read)
    self.assertEqual(25, event.written)
    
    event = _get_event("650 BW 0 0")
    self.assertEqual(0, event.read)
    self.assertEqual(0, event.written)
    
    # BW events are documented as possibly having various keywords including
    # DIR, OR, EXIT, and APP in the future. This is kinda a pointless note
    # since tor doesn't actually do it yet (and likely never will), but might
    # as well sanity test that it'll be ok.
    
    event = _get_event("650 BW 10 20 OR=5 EXIT=500")
    self.assertEqual(10, event.read)
    self.assertEqual(20, event.written)
    self.assertEqual({'OR': '5', 'EXIT': '500'}, event.keyword_args)
    
    self.assertRaises(ProtocolError, _get_event, "650 BW")
    self.assertRaises(ProtocolError, _get_event, "650 BW 15")
    self.assertRaises(ProtocolError, _get_event, "650 BW -15 25")
    self.assertRaises(ProtocolError, _get_event, "650 BW 15 -25")
    self.assertRaises(ProtocolError, _get_event, "650 BW x 25")
  
  def test_circ_event(self):
    event = _get_event(CIRC_LAUNCHED)
    
    self.assertTrue(isinstance(event, stem.response.events.CircuitEvent))
    self.assertEqual(CIRC_LAUNCHED.lstrip("650 "), str(event))
    self.assertEqual("7", event.id)
    self.assertEqual(CircStatus.LAUNCHED, event.status)
    self.assertEqual((), event.path)
    self.assertEqual((CircBuildFlag.NEED_CAPACITY,), event.build_flags)
    self.assertEqual(CircPurpose.GENERAL, event.purpose)
    self.assertEqual(None, event.hs_state)
    self.assertEqual(None, event.rend_query)
    self.assertEqual(datetime.datetime(2012, 11, 8, 16, 48, 38, 417238), event.created)
    self.assertEqual(None, event.reason)
    self.assertEqual(None, event.remote_reason)
    
    event = _get_event(CIRC_EXTENDED)
    
    self.assertTrue(isinstance(event, stem.response.events.CircuitEvent))
    self.assertEqual(CIRC_EXTENDED.lstrip("650 "), str(event))
    self.assertEqual("7", event.id)
    self.assertEqual(CircStatus.EXTENDED, event.status)
    self.assertEqual((("999A226EBED397F331B612FE1E4CFAE5C1F201BA", "piyaz"),), event.path)
    self.assertEqual((CircBuildFlag.NEED_CAPACITY,), event.build_flags)
    self.assertEqual(CircPurpose.GENERAL, event.purpose)
    self.assertEqual(None, event.hs_state)
    self.assertEqual(None, event.rend_query)
    self.assertEqual(datetime.datetime(2012, 11, 8, 16, 48, 38, 417238), event.created)
    self.assertEqual(None, event.reason)
    self.assertEqual(None, event.remote_reason)
    
    event = _get_event(CIRC_FAILED)
    
    self.assertTrue(isinstance(event, stem.response.events.CircuitEvent))
    self.assertEqual(CIRC_FAILED.lstrip("650 "), str(event))
    self.assertEqual("5", event.id)
    self.assertEqual(CircStatus.FAILED, event.status)
    self.assertEqual((("E57A476CD4DFBD99B4EE52A100A58610AD6E80B9", "ergebnisoffen"),), event.path)
    self.assertEqual((CircBuildFlag.NEED_CAPACITY,), event.build_flags)
    self.assertEqual(CircPurpose.GENERAL, event.purpose)
    self.assertEqual(None, event.hs_state)
    self.assertEqual(None, event.rend_query)
    self.assertEqual(datetime.datetime(2012, 11, 8, 16, 48, 36, 400959), event.created)
    self.assertEqual(CircClosureReason.DESTROYED, event.reason)
    self.assertEqual(CircClosureReason.OR_CONN_CLOSED, event.remote_reason)
    
    event = _get_event(CIRC_LAUNCHED_OLD)
    
    self.assertTrue(isinstance(event, stem.response.events.CircuitEvent))
    self.assertEqual(CIRC_LAUNCHED_OLD.lstrip("650 "), str(event))
    self.assertEqual("4", event.id)
    self.assertEqual(CircStatus.LAUNCHED, event.status)
    self.assertEqual((), event.path)
    self.assertEqual(None, event.build_flags)
    self.assertEqual(None, event.purpose)
    self.assertEqual(None, event.hs_state)
    self.assertEqual(None, event.rend_query)
    self.assertEqual(None, event.created)
    self.assertEqual(None, event.reason)
    self.assertEqual(None, event.remote_reason)
    
    event = _get_event(CIRC_EXTENDED_OLD)
    
    self.assertTrue(isinstance(event, stem.response.events.CircuitEvent))
    self.assertEqual(CIRC_EXTENDED_OLD.lstrip("650 "), str(event))
    self.assertEqual("1", event.id)
    self.assertEqual(CircStatus.EXTENDED, event.status)
    self.assertEqual((("E57A476CD4DFBD99B4EE52A100A58610AD6E80B9", None), (None,"hamburgerphone")), event.path)
    self.assertEqual(None, event.build_flags)
    self.assertEqual(None, event.purpose)
    self.assertEqual(None, event.hs_state)
    self.assertEqual(None, event.rend_query)
    self.assertEqual(None, event.created)
    self.assertEqual(None, event.reason)
    self.assertEqual(None, event.remote_reason)
    
    event = _get_event(CIRC_BUILT_OLD)
    
    self.assertTrue(isinstance(event, stem.response.events.CircuitEvent))
    self.assertEqual(CIRC_BUILT_OLD.lstrip("650 "), str(event))
    self.assertEqual("1", event.id)
    self.assertEqual(CircStatus.BUILT, event.status)
    self.assertEqual((("E57A476CD4DFBD99B4EE52A100A58610AD6E80B9", None), (None,"hamburgerphone"), (None, "PrivacyRepublic14")), event.path)
    self.assertEqual(None, event.build_flags)
    self.assertEqual(None, event.purpose)
    self.assertEqual(None, event.hs_state)
    self.assertEqual(None, event.rend_query)
    self.assertEqual(None, event.created)
    self.assertEqual(None, event.reason)
    self.assertEqual(None, event.remote_reason)
    
    # malformed TIME_CREATED timestamp
    self.assertRaises(ProtocolError, _get_event, CIRC_LAUNCHED_BAD_1)
    
    # invalid circuit id
    self.assertRaises(ProtocolError, _get_event, CIRC_LAUNCHED_BAD_2)
  
  def test_circ_minor_event(self):
    event = _get_event(CIRC_MINOR_EVENT)
    
    self.assertTrue(isinstance(event, stem.response.events.CircMinorEvent))
    self.assertEqual(CIRC_MINOR_EVENT.lstrip("650 "), str(event))
    self.assertEqual("7", event.id)
    self.assertEqual(CircEvent.PURPOSE_CHANGED, event.event)
    self.assertEqual((("67B2BDA4264D8A189D9270E28B1D30A262838243", "europa1"),), event.path)
    self.assertEqual((CircBuildFlag.IS_INTERNAL, CircBuildFlag.NEED_CAPACITY), event.build_flags)
    self.assertEqual(CircPurpose.MEASURE_TIMEOUT, event.purpose)
    self.assertEqual(None, event.hs_state)
    self.assertEqual(None, event.rend_query)
    self.assertEqual(datetime.datetime(2012, 12, 3, 16, 45, 33, 409602), event.created)
    self.assertEqual(CircPurpose.TESTING, event.old_purpose)
    self.assertEqual(None, event.old_hs_state)
    
    # malformed TIME_CREATED timestamp
    self.assertRaises(ProtocolError, _get_event, CIRC_MINOR_EVENT_BAD_1)
    
    # invalid circuit id
    self.assertRaises(ProtocolError, _get_event, CIRC_MINOR_EVENT_BAD_2)
  
  def test_clients_seen_event(self):
    event = _get_event(CLIENTS_SEEN_EVENT)
    
    self.assertTrue(isinstance(event, stem.response.events.ClientsSeenEvent))
    self.assertEqual(CLIENTS_SEEN_EVENT.lstrip("650 "), str(event))
    self.assertEqual(datetime.datetime(2008, 12, 25, 23, 50, 43), event.start_time)
    self.assertEqual({'us': 16, 'de': 8, 'uk': 8}, event.locales)
    self.assertEqual({'v4': 16, 'v6': 40}, event.ip_versions)
    
    # CountrySummary's 'key=value' mappings are replaced with 'key:value'
    self.assertRaises(ProtocolError, _get_event, CLIENTS_SEEN_EVENT_BAD_1)
    
    # CountrySummary's country codes aren't two letters
    self.assertRaises(ProtocolError, _get_event, CLIENTS_SEEN_EVENT_BAD_2)
    
    # CountrySummary's mapping contains a non-numeric value
    self.assertRaises(ProtocolError, _get_event, CLIENTS_SEEN_EVENT_BAD_3)
    
    # CountrySummary has duplicate country codes (multiple 'au=' mappings)
    self.assertRaises(ProtocolError, _get_event, CLIENTS_SEEN_EVENT_BAD_4)
    
    # IPVersions's 'key=value' mappings are replaced with 'key:value'
    self.assertRaises(ProtocolError, _get_event, CLIENTS_SEEN_EVENT_BAD_5)
    
    # IPVersions's mapping contains a non-numeric value
    self.assertRaises(ProtocolError, _get_event, CLIENTS_SEEN_EVENT_BAD_6)
  
  def test_conf_changed(self):
    event = _get_event(CONF_CHANGED_EVENT)
    
    expected_config = {
      'ExitNodes': 'caerSidi',
      'MaxCircuitDirtiness': '20',
      'ExitPolicy': None,
    }
    
    self.assertTrue(isinstance(event, stem.response.events.ConfChangedEvent))
    self.assertEqual(expected_config, event.config)
  
  def test_descchanged_event(self):
    # all we can check for is that the event is properly parsed as a
    # DescChangedEvent instance
    
    event = _get_event("650 DESCCHANGED")
    
    self.assertTrue(isinstance(event, stem.response.events.DescChangedEvent))
    self.assertEqual("DESCCHANGED", str(event))
    self.assertEqual([], event.positional_args)
    self.assertEqual({}, event.keyword_args)
  
  def test_guard_event(self):
    event = _get_event(GUARD_NEW)
    
    self.assertTrue(isinstance(event, stem.response.events.GuardEvent))
    self.assertEqual(GUARD_NEW.lstrip("650 "), str(event))
    self.assertEqual(GuardType.ENTRY, event.guard_type)
    self.assertEqual("$36B5DBA788246E8369DBAF58577C6BC044A9A374", event.name)
    self.assertEqual(GuardStatus.NEW, event.status)
    
    event = _get_event(GUARD_GOOD)
    self.assertEqual(GuardType.ENTRY, event.guard_type)
    self.assertEqual("$5D0034A368E0ABAF663D21847E1C9B6CFA09752A", event.name)
    self.assertEqual(GuardStatus.GOOD, event.status)
    
    event = _get_event(GUARD_BAD)
    self.assertEqual(GuardType.ENTRY, event.guard_type)
    self.assertEqual("$5D0034A368E0ABAF663D21847E1C9B6CFA09752A", event.name)
    self.assertEqual(GuardStatus.BAD, event.status)
  
  def test_newdesc_event(self):
    event = _get_event(NEWDESC_SINGLE)
    expected_relays = (("B3FA3110CC6F42443F039220C134CBD2FC4F0493", "Sakura"),)
    
    self.assertTrue(isinstance(event, stem.response.events.NewDescEvent))
    self.assertEqual(NEWDESC_SINGLE.lstrip("650 "), str(event))
    self.assertEqual(expected_relays, event.relays)
    
    event = _get_event(NEWDESC_MULTIPLE)
    expected_relays = (("BE938957B2CA5F804B3AFC2C1EE6673170CDBBF8", "Moonshine"),
                       ("B4BE08B22D4D2923EDC3970FD1B93D0448C6D8FF", "Unnamed"))
    
    self.assertTrue(isinstance(event, stem.response.events.NewDescEvent))
    self.assertEqual(NEWDESC_MULTIPLE.lstrip("650 "), str(event))
    self.assertEqual(expected_relays, event.relays)
  
  def test_new_consensus_event(self):
    expected_desc = []
    
    expected_desc.append(mocking.get_router_status_entry_v3({
      "r": "Beaver /96bKo4soysolMgKn5Hex2nyFSY pAJH9dSBp/CG6sPhhVY/5bLaVPM 2012-12-02 22:02:45 77.223.43.54 9001 0",
      "s": "Fast Named Running Stable Valid",
    }))
    
    expected_desc.append(mocking.get_router_status_entry_v3({
      "r": "Unnamed /+fJRWjmIGNAL2C5rRZHq3R91tA 7AnpZjfdBpYzXnMNm+w1bTsFF6Y 2012-12-02 17:51:10 91.121.184.87 9001 0",
      "s": "Fast Guard Running Stable Valid",
    }))
    
    event = _get_event(NEWCONSENSUS_EVENT)
    
    self.assertTrue(isinstance(event, stem.response.events.NewConsensusEvent))
    self.assertEqual(expected_desc, event.desc)
  
  def test_ns_event(self):
    expected_desc = mocking.get_router_status_entry_v3({
      "r": "whnetz dbBxYcJriTTrcxsuy4PUZcMRwCA VStM7KAIH/mXXoGDUpoGB1OXufg 2012-12-02 21:03:56 141.70.120.13 9001 9030",
      "s": "Fast HSDir Named Stable V2Dir Valid",
    })
    
    event = _get_event(NS_EVENT)
    
    self.assertTrue(isinstance(event, stem.response.events.NetworkStatusEvent))
    self.assertEqual([expected_desc], event.desc)
  
  def test_orconn_event(self):
    event = _get_event(ORCONN_CLOSED)
    
    self.assertTrue(isinstance(event, stem.response.events.ORConnEvent))
    self.assertEqual(ORCONN_CLOSED.lstrip("650 "), str(event))
    self.assertEqual("$A1130635A0CDA6F60C276FBF6994EFBD4ECADAB1~tama", event.endpoint)
    self.assertEqual("A1130635A0CDA6F60C276FBF6994EFBD4ECADAB1", event.endpoint_fingerprint)
    self.assertEqual("tama", event.endpoint_nickname)
    self.assertEqual(None, event.endpoint_address)
    self.assertEqual(None, event.endpoint_port)
    self.assertEqual(ORStatus.CLOSED, event.status)
    self.assertEqual(ORClosureReason.DONE, event.reason)
    self.assertEqual(None, event.circ_count)
    
    event = _get_event(ORCONN_CONNECTED)
    
    self.assertTrue(isinstance(event, stem.response.events.ORConnEvent))
    self.assertEqual(ORCONN_CONNECTED.lstrip("650 "), str(event))
    self.assertEqual("127.0.0.1:9000", event.endpoint)
    self.assertEqual(None, event.endpoint_fingerprint)
    self.assertEqual(None, event.endpoint_nickname)
    self.assertEqual('127.0.0.1', event.endpoint_address)
    self.assertEqual(9000, event.endpoint_port)
    self.assertEqual(ORStatus.CONNECTED, event.status)
    self.assertEqual(None, event.reason)
    self.assertEqual(20, event.circ_count)
    
    event = _get_event(ORCONN_LAUNCHED)
    
    self.assertTrue(isinstance(event, stem.response.events.ORConnEvent))
    self.assertEqual(ORCONN_LAUNCHED.lstrip("650 "), str(event))
    self.assertEqual("$7ED90E2833EE38A75795BA9237B0A4560E51E1A0=GreenDragon", event.endpoint)
    self.assertEqual("7ED90E2833EE38A75795BA9237B0A4560E51E1A0", event.endpoint_fingerprint)
    self.assertEqual("GreenDragon", event.endpoint_nickname)
    self.assertEqual(None, event.endpoint_address)
    self.assertEqual(None, event.endpoint_port)
    self.assertEqual(ORStatus.LAUNCHED, event.status)
    self.assertEqual(None, event.reason)
    self.assertEqual(None, event.circ_count)
    
    # malformed fingerprint
    self.assertRaises(ProtocolError, _get_event, ORCONN_BAD_1)
    
    # invalid port number ('001')
    self.assertRaises(ProtocolError, _get_event, ORCONN_BAD_2)
    
    # non-numeric NCIRCS
    self.assertRaises(ProtocolError, _get_event, ORCONN_BAD_3)
  
  def test_signal_event(self):
    event = _get_event("650 SIGNAL DEBUG")
    self.assertTrue(isinstance(event, stem.response.events.SignalEvent))
    self.assertEqual("SIGNAL DEBUG", str(event))
    self.assertEqual(Signal.DEBUG, event.signal)
    
    event = _get_event("650 SIGNAL DUMP")
    self.assertEqual(Signal.DUMP, event.signal)
  
  def test_status_event_consensus_arrived(self):
    event = _get_event(STATUS_GENERAL_CONSENSUS_ARRIVED)
    
    self.assertTrue(isinstance(event, stem.response.events.StatusEvent))
    self.assertEqual(STATUS_GENERAL_CONSENSUS_ARRIVED.lstrip("650 "), str(event))
    self.assertEqual(StatusType.GENERAL, event.status_type)
    self.assertEqual(Runlevel.NOTICE, event.runlevel)
    self.assertEqual("CONSENSUS_ARRIVED", event.action)
  
  def test_status_event_enough_dir_info(self):
    event = _get_event(STATUS_CLIENT_ENOUGH_DIR_INFO)
    
    self.assertEqual(StatusType.CLIENT, event.status_type)
    self.assertEqual(Runlevel.NOTICE, event.runlevel)
    self.assertEqual("ENOUGH_DIR_INFO", event.action)
  
  def test_status_event_circuit_established(self):
    event = _get_event(STATUS_CLIENT_CIRC_ESTABLISHED)
    
    self.assertEqual(StatusType.CLIENT, event.status_type)
    self.assertEqual(Runlevel.NOTICE, event.runlevel)
    self.assertEqual("CIRCUIT_ESTABLISHED", event.action)
  
  def test_status_event_bootstrap_descriptors(self):
    event = _get_event(STATUS_CLIENT_BOOTSTRAP_DESCRIPTORS)
    
    self.assertEqual(StatusType.CLIENT, event.status_type)
    self.assertEqual(Runlevel.NOTICE, event.runlevel)
    self.assertEqual("BOOTSTRAP", event.action)
    
    expected_attr = {
      'PROGRESS': '53',
      'TAG': 'loading_descriptors',
      'SUMMARY': 'Loading relay descriptors',
    }
    
    self.assertEqual(expected_attr, event.keyword_args)
  
  def test_status_event_bootstrap_stuck(self):
    event = _get_event(STATUS_CLIENT_BOOTSTRAP_STUCK)
    
    self.assertEqual(StatusType.CLIENT, event.status_type)
    self.assertEqual(Runlevel.WARN, event.runlevel)
    self.assertEqual("BOOTSTRAP", event.action)
    
    expected_attr = {
      'PROGRESS': '80',
      'TAG': 'conn_or',
      'SUMMARY': 'Connecting to the Tor network',
      'WARNING': 'Network is unreachable',
      'REASON': 'NOROUTE',
      'COUNT': '5',
      'RECOMMENDATION': 'warn',
    }
    
    self.assertEqual(expected_attr, event.keyword_args)
  
  def test_status_event_bootstrap_connecting(self):
    event = _get_event(STATUS_CLIENT_BOOTSTRAP_CONNECTING)
    
    self.assertEqual(StatusType.CLIENT, event.status_type)
    self.assertEqual(Runlevel.NOTICE, event.runlevel)
    self.assertEqual("BOOTSTRAP", event.action)
    
    expected_attr = {
      'PROGRESS': '80',
      'TAG': 'conn_or',
      'SUMMARY': 'Connecting to the Tor network',
    }
    
    self.assertEqual(expected_attr, event.keyword_args)
  
  def test_status_event_bootstrap_first_handshake(self):
    event = _get_event(STATUS_CLIENT_BOOTSTRAP_FIRST_HANDSHAKE)
    
    self.assertEqual(StatusType.CLIENT, event.status_type)
    self.assertEqual(Runlevel.NOTICE, event.runlevel)
    self.assertEqual("BOOTSTRAP", event.action)
    
    expected_attr = {
      'PROGRESS': '85',
      'TAG': 'handshake_or',
      'SUMMARY': 'Finishing handshake with first hop',
    }
    
    self.assertEqual(expected_attr, event.keyword_args)
  
  def test_status_event_bootstrap_established(self):
    event = _get_event(STATUS_CLIENT_BOOTSTRAP_ESTABLISHED)
    
    self.assertEqual(StatusType.CLIENT, event.status_type)
    self.assertEqual(Runlevel.NOTICE, event.runlevel)
    self.assertEqual("BOOTSTRAP", event.action)
    
    expected_attr = {
      'PROGRESS': '90',
      'TAG': 'circuit_create',
      'SUMMARY': 'Establishing a Tor circuit',
    }
    
    self.assertEqual(expected_attr, event.keyword_args)
  
  def test_status_event_bootstrap_done(self):
    event = _get_event(STATUS_CLIENT_BOOTSTRAP_DONE)
    
    self.assertEqual(StatusType.CLIENT, event.status_type)
    self.assertEqual(Runlevel.NOTICE, event.runlevel)
    self.assertEqual("BOOTSTRAP", event.action)
    
    expected_attr = {
      'PROGRESS': '100',
      'TAG': 'done',
      'SUMMARY': 'Done',
    }
    
    self.assertEqual(expected_attr, event.keyword_args)
  
  def test_status_event_bootstrap_check_reachability(self):
    event = _get_event(STATUS_SERVER_CHECK_REACHABILITY)
    
    self.assertEqual(StatusType.SERVER, event.status_type)
    self.assertEqual(Runlevel.NOTICE, event.runlevel)
    self.assertEqual("CHECKING_REACHABILITY", event.action)
    
    expected_attr = {
      'ORADDRESS': '71.35.143.230:9050',
    }
    
    self.assertEqual(expected_attr, event.keyword_args)
  
  def test_status_event_dns_timeout(self):
    event = _get_event(STATUS_SERVER_DNS_TIMEOUT)
    
    self.assertEqual(StatusType.SERVER, event.status_type)
    self.assertEqual(Runlevel.NOTICE, event.runlevel)
    self.assertEqual("NAMESERVER_STATUS", event.action)
    
    expected_attr = {
      'NS': '205.171.3.25',
      'STATUS': 'DOWN',
      'ERR': 'request timed out.',
    }
    
    self.assertEqual(expected_attr, event.keyword_args)
  
  def test_status_event_dns_down(self):
    event = _get_event(STATUS_SERVER_DNS_DOWN)
    
    self.assertEqual(StatusType.SERVER, event.status_type)
    self.assertEqual(Runlevel.WARN, event.runlevel)
    self.assertEqual("NAMESERVER_ALL_DOWN", event.action)
  
  def test_status_event_dns_up(self):
    event = _get_event(STATUS_SERVER_DNS_UP)
    
    self.assertEqual(StatusType.SERVER, event.status_type)
    self.assertEqual(Runlevel.NOTICE, event.runlevel)
    self.assertEqual("NAMESERVER_STATUS", event.action)
    
    expected_attr = {
      'NS': '205.171.3.25',
      'STATUS': 'UP',
    }
    
    self.assertEqual(expected_attr, event.keyword_args)
  
  def test_status_event_bug(self):
    # briefly insert a fake value in EVENT_TYPE_TO_CLASS
    stem.response.events.EVENT_TYPE_TO_CLASS['STATUS_SPECIFIC'] = stem.response.events.StatusEvent
    self.assertRaises(ValueError, _get_event, STATUS_SPECIFIC_CONSENSUS_ARRIVED)
    del stem.response.events.EVENT_TYPE_TO_CLASS['STATUS_SPECIFIC']
  
  def test_stream_event(self):
    event = _get_event(STREAM_NEW)
    
    self.assertTrue(isinstance(event, stem.response.events.StreamEvent))
    self.assertEqual(STREAM_NEW.lstrip("650 "), str(event))
    self.assertEqual("18", event.id)
    self.assertEqual(StreamStatus.NEW, event.status)
    self.assertEqual(None, event.circ_id)
    self.assertEqual("encrypted.google.com:443", event.target)
    self.assertEqual("encrypted.google.com", event.target_address)
    self.assertEqual(443, event.target_port)
    self.assertEqual(None, event.reason)
    self.assertEqual(None, event.remote_reason)
    self.assertEqual(None, event.source)
    self.assertEqual("127.0.0.1:47849", event.source_addr)
    self.assertEqual("127.0.0.1", event.source_address)
    self.assertEqual(47849, event.source_port)
    self.assertEqual(StreamPurpose.USER, event.purpose)
    
    event = _get_event(STREAM_SENTCONNECT)
    
    self.assertTrue(isinstance(event, stem.response.events.StreamEvent))
    self.assertEqual(STREAM_SENTCONNECT.lstrip("650 "), str(event))
    self.assertEqual("18", event.id)
    self.assertEqual(StreamStatus.SENTCONNECT, event.status)
    self.assertEqual("26", event.circ_id)
    self.assertEqual("encrypted.google.com:443", event.target)
    self.assertEqual("encrypted.google.com", event.target_address)
    self.assertEqual(443, event.target_port)
    self.assertEqual(None, event.reason)
    self.assertEqual(None, event.remote_reason)
    self.assertEqual(None, event.source)
    self.assertEqual(None, event.source_addr)
    self.assertEqual(None, event.source_address)
    self.assertEqual(None, event.source_port)
    self.assertEqual(None, event.purpose)
    
    event = _get_event(STREAM_REMAP)
    
    self.assertTrue(isinstance(event, stem.response.events.StreamEvent))
    self.assertEqual(STREAM_REMAP.lstrip("650 "), str(event))
    self.assertEqual("18", event.id)
    self.assertEqual(StreamStatus.REMAP, event.status)
    self.assertEqual("26", event.circ_id)
    self.assertEqual("74.125.227.129:443", event.target)
    self.assertEqual("74.125.227.129", event.target_address)
    self.assertEqual(443, event.target_port)
    self.assertEqual(None, event.reason)
    self.assertEqual(None, event.remote_reason)
    self.assertEqual(StreamSource.EXIT, event.source)
    self.assertEqual(None, event.source_addr)
    self.assertEqual(None, event.source_address)
    self.assertEqual(None, event.source_port)
    self.assertEqual(None, event.purpose)
    
    event = _get_event(STREAM_SUCCEEDED)
    
    self.assertTrue(isinstance(event, stem.response.events.StreamEvent))
    self.assertEqual(STREAM_SUCCEEDED.lstrip("650 "), str(event))
    self.assertEqual("18", event.id)
    self.assertEqual(StreamStatus.SUCCEEDED, event.status)
    self.assertEqual("26", event.circ_id)
    self.assertEqual("74.125.227.129:443", event.target)
    self.assertEqual("74.125.227.129", event.target_address)
    self.assertEqual(443, event.target_port)
    self.assertEqual(None, event.reason)
    self.assertEqual(None, event.remote_reason)
    self.assertEqual(None, event.source)
    self.assertEqual(None, event.source_addr)
    self.assertEqual(None, event.source_address)
    self.assertEqual(None, event.source_port)
    self.assertEqual(None, event.purpose)
    
    event = _get_event(STREAM_CLOSED_RESET)
    
    self.assertTrue(isinstance(event, stem.response.events.StreamEvent))
    self.assertEqual(STREAM_CLOSED_RESET.lstrip("650 "), str(event))
    self.assertEqual("21", event.id)
    self.assertEqual(StreamStatus.CLOSED, event.status)
    self.assertEqual("26", event.circ_id)
    self.assertEqual("74.125.227.129:443", event.target)
    self.assertEqual("74.125.227.129", event.target_address)
    self.assertEqual(443, event.target_port)
    self.assertEqual(StreamClosureReason.CONNRESET, event.reason)
    self.assertEqual(None, event.remote_reason)
    self.assertEqual(None, event.source)
    self.assertEqual(None, event.source_addr)
    self.assertEqual(None, event.source_address)
    self.assertEqual(None, event.source_port)
    self.assertEqual(None, event.purpose)
    
    event = _get_event(STREAM_CLOSED_DONE)
    
    self.assertTrue(isinstance(event, stem.response.events.StreamEvent))
    self.assertEqual(STREAM_CLOSED_DONE.lstrip("650 "), str(event))
    self.assertEqual("25", event.id)
    self.assertEqual(StreamStatus.CLOSED, event.status)
    self.assertEqual("26", event.circ_id)
    self.assertEqual("199.7.52.72:80", event.target)
    self.assertEqual("199.7.52.72", event.target_address)
    self.assertEqual(80, event.target_port)
    self.assertEqual(StreamClosureReason.DONE, event.reason)
    self.assertEqual(None, event.remote_reason)
    self.assertEqual(None, event.source)
    self.assertEqual(None, event.source_addr)
    self.assertEqual(None, event.source_address)
    self.assertEqual(None, event.source_port)
    self.assertEqual(None, event.purpose)
    
    event = _get_event(STREAM_DIR_FETCH)
    
    self.assertTrue(isinstance(event, stem.response.events.StreamEvent))
    self.assertEqual(STREAM_DIR_FETCH.lstrip("650 "), str(event))
    self.assertEqual("14", event.id)
    self.assertEqual(StreamStatus.NEW, event.status)
    self.assertEqual(None, event.circ_id)
    self.assertEqual("176.28.51.238.$649F2D0ACF418F7CFC6539AB2257EB2D5297BAFA.exit:443", event.target)
    self.assertEqual("176.28.51.238.$649F2D0ACF418F7CFC6539AB2257EB2D5297BAFA.exit", event.target_address)
    self.assertEqual(443, event.target_port)
    self.assertEqual(None, event.reason)
    self.assertEqual(None, event.remote_reason)
    self.assertEqual(None, event.source)
    self.assertEqual("(Tor_internal):0", event.source_addr)
    self.assertEqual("(Tor_internal)", event.source_address)
    self.assertEqual(0, event.source_port)
    self.assertEqual(StreamPurpose.DIR_FETCH, event.purpose)
    
    event = _get_event(STREAM_DNS_REQUEST)
    
    self.assertTrue(isinstance(event, stem.response.events.StreamEvent))
    self.assertEqual(STREAM_DNS_REQUEST.lstrip("650 "), str(event))
    self.assertEqual("1113", event.id)
    self.assertEqual(StreamStatus.NEW, event.status)
    self.assertEqual(None, event.circ_id)
    self.assertEqual("www.google.com:0", event.target)
    self.assertEqual("www.google.com", event.target_address)
    self.assertEqual(0, event.target_port)
    self.assertEqual(None, event.reason)
    self.assertEqual(None, event.remote_reason)
    self.assertEqual(None, event.source)
    self.assertEqual("127.0.0.1:15297", event.source_addr)
    self.assertEqual("127.0.0.1", event.source_address)
    self.assertEqual(15297, event.source_port)
    self.assertEqual(StreamPurpose.DNS_REQUEST, event.purpose)
    
    # missing target
    self.assertRaises(ProtocolError, _get_event, STREAM_SENTCONNECT_BAD_1)
    
    # target is missing a port
    self.assertRaises(ProtocolError, _get_event, STREAM_SENTCONNECT_BAD_2)
    
    # target's port is malformed
    self.assertRaises(ProtocolError, _get_event, STREAM_SENTCONNECT_BAD_3)
    
    # SOURCE_ADDR is missing a port
    self.assertRaises(ProtocolError, _get_event, STREAM_DNS_REQUEST_BAD_1)
    
    # SOURCE_ADDR's port is malformed
    self.assertRaises(ProtocolError, _get_event, STREAM_DNS_REQUEST_BAD_2)
  
  def test_stream_bw_event(self):
    event = _get_event("650 STREAM_BW 2 15 25")
    
    self.assertTrue(isinstance(event, stem.response.events.StreamBwEvent))
    self.assertEqual("2", event.id)
    self.assertEqual(15, event.written)
    self.assertEqual(25, event.read)
    
    event = _get_event("650 STREAM_BW Stream02 0 0")
    self.assertEqual("Stream02", event.id)
    self.assertEqual(0, event.written)
    self.assertEqual(0, event.read)
    
    self.assertRaises(ProtocolError, _get_event, "650 STREAM_BW")
    self.assertRaises(ProtocolError, _get_event, "650 STREAM_BW 2")
    self.assertRaises(ProtocolError, _get_event, "650 STREAM_BW 2 15")
    self.assertRaises(ProtocolError, _get_event, "650 STREAM_BW - 15 25")
    self.assertRaises(ProtocolError, _get_event, "650 STREAM_BW 12345678901234567 15 25")
    self.assertRaises(ProtocolError, _get_event, "650 STREAM_BW 2 -15 25")
    self.assertRaises(ProtocolError, _get_event, "650 STREAM_BW 2 15 -25")
    self.assertRaises(ProtocolError, _get_event, "650 STREAM_BW 2 x 25")
  
  def test_unrecognized_enum_logging(self):
    """
    Checks that when event parsing gets a value that isn't recognized by stem's
    enumeration of the attribute that we log a message.
    """
    
    stem_logger = stem.util.log.get_logger()
    logging_buffer = stem.util.log.LogBuffer(stem.util.log.INFO)
    stem_logger.addHandler(logging_buffer)
    
    # Try parsing a valid event. We shouldn't log anything.
    
    _get_event(STATUS_GENERAL_CONSENSUS_ARRIVED)
    self.assertTrue(logging_buffer.is_empty())
    self.assertEqual([], list(logging_buffer))
    
    # Parse an invalid runlevel.
    
    _get_event(STATUS_GENERAL_CONSENSUS_ARRIVED.replace("NOTICE", "OMEGA_CRITICAL!!!"))
    logged_events = list(logging_buffer)
    
    self.assertEqual(1, len(logged_events))
    self.assertTrue("STATUS_GENERAL event had an unrecognized runlevel" in logged_events[0])
    
    stem_logger.removeHandler(logging_buffer)

