"""
Integration tests for the stem.control.Controller class.
"""

from __future__ import with_statement

import os
import re
import shutil
import socket
import tempfile
import threading
import time
import unittest

import stem.connection
import stem.control
import stem.descriptor.reader
import stem.descriptor.router_status_entry
import stem.response.protocolinfo
import stem.socket
import stem.version
import test.network
import test.runner
import test.util

from stem.control import EventType
from stem.version import Requirement

class TestController(unittest.TestCase):
  def test_from_port(self):
    """
    Basic sanity check for the from_port constructor.
    """
    
    if test.runner.require_control(self): return
    
    if test.runner.Torrc.PORT in test.runner.get_runner().get_options():
      with stem.control.Controller.from_port(control_port = test.runner.CONTROL_PORT) as controller:
        self.assertTrue(isinstance(controller, stem.control.Controller))
    else:
      self.assertRaises(stem.SocketError, stem.control.Controller.from_port, "127.0.0.1", test.runner.CONTROL_PORT)
  
  def test_from_socket_file(self):
    """
    Basic sanity check for the from_socket_file constructor.
    """
    
    if test.runner.require_control(self): return
    
    if test.runner.Torrc.SOCKET in test.runner.get_runner().get_options():
      with stem.control.Controller.from_socket_file(socket_path = test.runner.CONTROL_SOCKET_PATH) as controller:
        self.assertTrue(isinstance(controller, stem.control.Controller))
    else:
      self.assertRaises(stem.SocketError, stem.control.Controller.from_socket_file, test.runner.CONTROL_SOCKET_PATH)
  
  def test_event_handling(self):
    """
    Add a couple listeners for various events and make sure that they receive
    them. Then remove the listeners.
    """
    
    if test.runner.require_control(self): return
    
    event_notice1, event_notice2 = threading.Event(), threading.Event()
    event_buffer1, event_buffer2 = [], []
    
    def listener1(event):
      event_buffer1.append(event)
      event_notice1.set()
    
    def listener2(event):
      event_buffer2.append(event)
      event_notice2.set()
    
    runner = test.runner.get_runner()
    with runner.get_tor_controller() as controller:
      controller.add_event_listener(listener1, EventType.BW)
      controller.add_event_listener(listener2, EventType.BW, EventType.DEBUG)
      
      # BW events occure at the rate of one per second, so wait a bit to let
      # some accumulate.
      
      event_notice1.wait(2)
      self.assertTrue(len(event_buffer1) >= 1)
      event_notice1.clear()
      
      event_notice2.wait(2)
      self.assertTrue(len(event_buffer2) >= 1)
      event_notice2.clear()
      
      # Checking that a listener's no longer called after being removed.
      
      controller.remove_event_listener(listener2)
      
      buffer2_size = len(event_buffer2)
      
      event_notice1.wait(2)
      self.assertTrue(len(event_buffer1) >= 2)
      
      event_notice2.wait(2)
      self.assertEqual(buffer2_size, len(event_buffer2))
      
      for event in event_buffer1:
        self.assertTrue(isinstance(event, stem.response.events.Event))
        self.assertEqual(2, len(event.positional_args))
        self.assertEqual({}, event.keyword_args)
        
        self.assertTrue(isinstance(event, stem.response.events.BandwidthEvent))
        self.assertTrue(hasattr(event, 'read'))
        self.assertTrue(hasattr(event, 'written'))
  
  def test_reattaching_listeners(self):
    """
    Checks that event listeners are re-attached when a controller disconnects
    then reconnects to tor.
    """
    
    if test.runner.require_control(self): return
    
    event_notice = threading.Event()
    event_buffer = []
    
    def listener(event):
      event_buffer.append(event)
      event_notice.set()
    
    runner = test.runner.get_runner()
    with runner.get_tor_controller() as controller:
      controller.add_event_listener(listener, EventType.BW)
      
      # get a BW event or two
      
      event_notice.wait(2)
      self.assertTrue(len(event_buffer) >= 1)
      
      # disconnect and check that we stop getting events
      
      controller.close()
      event_notice.clear()
      event_buffer = []
      
      event_notice.wait(2)
      self.assertTrue(len(event_buffer) == 0)
      
      # reconnect and check that we get events again
      
      controller.connect()
      controller.authenticate()
      
      event_notice.wait(2)
      self.assertTrue(len(event_buffer) >= 1)
      
      # disconnect
      
      controller.close()
      event_notice.clear()
      event_buffer = []
      
      # reconnect and check that we get events again
      
      controller.connect()
      stem.connection.authenticate(controller)
      
      event_notice.wait(2)
      self.assertTrue(len(event_buffer) >= 1)
      
      # disconnect
      
      controller.close()
      event_notice.clear()
      event_buffer = []
      
      # reconnect and check that we get events again
      
      controller.connect()
      controller.msg("AUTHENTICATE")
      
      event_notice.wait(2)
      self.assertTrue(len(event_buffer) >= 1)
  
  def test_getinfo(self):
    """
    Exercises GETINFO with valid and invalid queries.
    """
    
    if test.runner.require_control(self): return
    
    runner = test.runner.get_runner()
    
    with runner.get_tor_controller() as controller:
      # successful single query
      
      torrc_path = runner.get_torrc_path()
      self.assertEqual(torrc_path, controller.get_info("config-file"))
      self.assertEqual(torrc_path, controller.get_info("config-file", "ho hum"))
      
      expected = {"config-file": torrc_path}
      self.assertEqual(expected, controller.get_info(["config-file"]))
      self.assertEqual(expected, controller.get_info(["config-file"], "ho hum"))
      
      # successful batch query, we don't know the values so just checking for
      # the keys
      
      getinfo_params = set(["version", "config-file", "config/names"])
      self.assertEqual(getinfo_params, set(controller.get_info(["version", "config-file", "config/names"]).keys()))
      
      # non-existant option
      
      self.assertRaises(stem.ControllerError, controller.get_info, "blarg")
      self.assertEqual("ho hum", controller.get_info("blarg", "ho hum"))
      
      # empty input
      
      self.assertRaises(stem.ControllerError, controller.get_info, "")
      self.assertEqual("ho hum", controller.get_info("", "ho hum"))
      
      self.assertEqual({}, controller.get_info([]))
      self.assertEqual({}, controller.get_info([], {}))
  
  def test_get_version(self):
    """
    Test that the convenient method get_version() works.
    """
    
    if test.runner.require_control(self): return
    
    runner = test.runner.get_runner()
    with runner.get_tor_controller() as controller:
      version = controller.get_version()
      self.assertTrue(isinstance(version, stem.version.Version))
      self.assertEqual(version, runner.get_tor_version())
  
  def test_authenticate(self):
    """
    Test that the convenient method authenticate() works.
    """
    
    if test.runner.require_control(self): return
    
    runner = test.runner.get_runner()
    with runner.get_tor_controller(False) as controller:
      controller.authenticate(test.runner.CONTROL_PASSWORD)
      test.runner.exercise_controller(self, controller)
  
  def test_protocolinfo(self):
    """
    Test that the convenient method protocolinfo() works.
    """
    
    if test.runner.require_control(self): return
    
    runner = test.runner.get_runner()
    
    with runner.get_tor_controller(False) as controller:
      protocolinfo = controller.get_protocolinfo()
      self.assertTrue(isinstance(protocolinfo, stem.response.protocolinfo.ProtocolInfoResponse))
      
      # Doing a sanity test on the ProtocolInfoResponse instance returned.
      tor_options = runner.get_options()
      tor_version = runner.get_tor_version()
      auth_methods = []
      
      if test.runner.Torrc.COOKIE in tor_options:
        auth_methods.append(stem.response.protocolinfo.AuthMethod.COOKIE)
        
        if tor_version.meets_requirements(stem.version.Requirement.AUTH_SAFECOOKIE):
          auth_methods.append(stem.response.protocolinfo.AuthMethod.SAFECOOKIE)
      
      if test.runner.Torrc.PASSWORD in tor_options:
        auth_methods.append(stem.response.protocolinfo.AuthMethod.PASSWORD)
      
      if not auth_methods:
        auth_methods.append(stem.response.protocolinfo.AuthMethod.NONE)
      
      self.assertEqual(tuple(auth_methods), protocolinfo.auth_methods)
  
  def test_getconf(self):
    """
    Exercises GETCONF with valid and invalid queries.
    """
    
    if test.runner.require_control(self): return
    
    runner = test.runner.get_runner()
    
    with runner.get_tor_controller() as controller:
      socket = controller.get_socket()
      if isinstance(socket, stem.socket.ControlPort):
        connection_value = str(socket.get_port())
        config_key = "ControlPort"
      elif isinstance(socket, stem.socket.ControlSocketFile):
        connection_value = str(socket.get_socket_path())
        config_key = "ControlSocket"
      
      # successful single query
      self.assertEqual(connection_value, controller.get_conf(config_key))
      self.assertEqual(connection_value, controller.get_conf(config_key, "la-di-dah"))
      
      # succeessful batch query
      expected = {config_key: [connection_value]}
      self.assertEqual(expected, controller.get_conf_map([config_key]))
      self.assertEqual(expected, controller.get_conf_map([config_key], "la-di-dah"))
      
      request_params = ["ControlPORT", "dirport", "datadirectory"]
      reply_params = controller.get_conf_map(request_params, multiple=False).keys()
      self.assertEqual(set(request_params), set(reply_params))
      
      # queries an option that is unset
      
      self.assertEqual(None, controller.get_conf("HTTPSProxy"))
      self.assertEqual("la-di-dah", controller.get_conf("HTTPSProxy", "la-di-dah"))
      self.assertEqual([], controller.get_conf("HTTPSProxy", [], multiple = True))
      
      # non-existant option(s)
      self.assertRaises(stem.InvalidArguments, controller.get_conf, "blarg")
      self.assertEqual("la-di-dah", controller.get_conf("blarg", "la-di-dah"))
      self.assertRaises(stem.InvalidArguments, controller.get_conf_map, "blarg")
      self.assertEqual({"blarg": "la-di-dah"}, controller.get_conf_map("blarg", "la-di-dah"))
      
      self.assertRaises(stem.InvalidRequest, controller.get_conf_map, ["blarg", "huadf"], multiple = True)
      self.assertEqual({"erfusdj": "la-di-dah", "afiafj": "la-di-dah"}, controller.get_conf_map(["erfusdj", "afiafj"], "la-di-dah", multiple = True))
      
      # multivalue configuration keys
      nodefamilies = [("abc", "xyz", "pqrs"), ("mno", "tuv", "wxyz")]
      controller.msg("SETCONF %s" % " ".join(["nodefamily=\"" + ",".join(x) + "\"" for x in nodefamilies]))
      self.assertEqual([",".join(n) for n in nodefamilies], controller.get_conf("nodefamily", multiple = True))
      controller.msg("RESETCONF NodeFamily")
      
      # empty input
      self.assertEqual(None, controller.get_conf(""))
      self.assertEqual({}, controller.get_conf_map([]))
      self.assertEqual({}, controller.get_conf_map([""]))
      self.assertEqual(None, controller.get_conf("          "))
      self.assertEqual({}, controller.get_conf_map(["    ", "        "]))
      
      self.assertEqual("la-di-dah", controller.get_conf("", "la-di-dah"))
      self.assertEqual({}, controller.get_conf_map("", "la-di-dah"))
      self.assertEqual({}, controller.get_conf_map([], "la-di-dah"))
  
  def test_set_conf(self):
    """
    Exercises set_conf(), reset_conf(), and set_options() methods with valid
    and invalid requests.
    """
    
    if test.runner.require_control(self): return
    
    runner = test.runner.get_runner()
    tmpdir = tempfile.mkdtemp()
    
    with runner.get_tor_controller() as controller:
      try:
        # successfully set a single option
        connlimit = int(controller.get_conf("ConnLimit"))
        controller.set_conf("connlimit", str(connlimit - 1))
        self.assertEqual(connlimit - 1, int(controller.get_conf("ConnLimit")))
        
        # successfully set a single list option
        exit_policy = ["accept *:7777", "reject *:*"]
        controller.set_conf("ExitPolicy", exit_policy)
        self.assertEqual(exit_policy, controller.get_conf("ExitPolicy", multiple = True))
        
        # fail to set a single option
        try:
          controller.set_conf("invalidkeyboo", "abcde")
          self.fail()
        except stem.InvalidArguments, exc:
          self.assertEqual(["invalidkeyboo"], exc.arguments)
        
        # resets configuration parameters
        controller.reset_conf("ConnLimit", "ExitPolicy")
        self.assertEqual(connlimit, int(controller.get_conf("ConnLimit")))
        self.assertEqual(None, controller.get_conf("ExitPolicy"))
        
        # successfully sets multiple config options
        controller.set_options({
          "connlimit": str(connlimit - 2),
          "contactinfo": "stem@testing",
        })
        
        self.assertEqual(connlimit - 2, int(controller.get_conf("ConnLimit")))
        self.assertEqual("stem@testing", controller.get_conf("contactinfo"))
        
        # fail to set multiple config options
        try:
          controller.set_options({
            "contactinfo": "stem@testing",
            "bombay": "vadapav",
          })
          self.fail()
        except stem.InvalidArguments, exc:
          self.assertEqual(["bombay"], exc.arguments)
        
        # context-sensitive keys (the only retched things for which order matters)
        controller.set_options((
          ("HiddenServiceDir", tmpdir),
          ("HiddenServicePort", "17234 127.0.0.1:17235"),
        ))
        
        self.assertEqual(tmpdir, controller.get_conf("HiddenServiceDir"))
        self.assertEqual("17234 127.0.0.1:17235", controller.get_conf("HiddenServicePort"))
      finally:
        # reverts configuration changes
        controller.set_options((
          ("ExitPolicy", "reject *:*"),
          ("ConnLimit", None),
          ("ContactInfo", None),
          ("HiddenServiceDir", None),
          ("HiddenServicePort", None),
        ), reset = True)
        
        shutil.rmtree(tmpdir)
  
  def test_loadconf(self):
    """
    Exercises Controller.load_conf with valid and invalid requests.
    """
    
    if test.runner.require_control(self): return
    elif test.runner.require_version(self, stem.version.Requirement.LOADCONF): return
    
    runner = test.runner.get_runner()
    
    with runner.get_tor_controller() as controller:
      oldconf = runner.get_torrc_contents()
      
      try:
        # invalid requests
        self.assertRaises(stem.InvalidRequest, controller.load_conf, "ContactInfo confloaded")
        try:
          controller.load_conf("Blahblah blah")
          self.fail()
        except stem.InvalidArguments, exc:
          self.assertEqual(["Blahblah"], exc.arguments)
        
        # valid config
        controller.load_conf(runner.get_torrc_contents() + "\nContactInfo confloaded\n")
        self.assertEqual("confloaded", controller.get_conf("ContactInfo"))
      finally:
        # reload original valid config
        controller.load_conf(oldconf)
  
  def test_saveconf(self):
    if test.runner.require_control(self): return
    
    runner = test.runner.get_runner()
    
    # only testing for success, since we need to run out of disk space to test
    # for failure
    with runner.get_tor_controller() as controller:
      oldconf = runner.get_torrc_contents()
      
      try:
        controller.set_conf("ContactInfo", "confsaved")
        controller.save_conf()
        with file(runner.get_torrc_path()) as torrcfile:
          self.assertTrue("\nContactInfo confsaved\n" in torrcfile.read())
      finally:
        controller.load_conf(oldconf)
        controller.save_conf()
  
  def test_get_socks_ports(self):
    """
    Test Controller.get_socks_ports against a running tor instance.
    """
    if test.runner.require_control(self): return
    
    runner = test.runner.get_runner()
    
    with runner.get_tor_controller() as controller:
      self.assertEqual([('127.0.0.1', 1112)], controller.get_socks_listeners())
  
  def test_enable_feature(self):
    """
    Test Controller.enable_feature with valid and invalid inputs.
    """
    
    if test.runner.require_control(self): return
    
    runner = test.runner.get_runner()
    
    with runner.get_tor_controller() as controller:
      if not test.runner.require_version(self, stem.version.Version("0.1.2.2-alpha")):
        controller.enable_feature("VERBOSE_NAMES")
      
      self.assertTrue(controller.is_feature_enabled("VERBOSE_NAMES"))
      
      orconn_output = controller.get_info('orconn-status')
      
      # the orconn-status results will be empty if we don't have a connection
      if orconn_output == '':
        if test.runner.require_online(self): return
      
      self.assertTrue("VERBOSE_NAMES" in controller._enabled_features)
      self.assertRaises(stem.InvalidArguments, controller.enable_feature, ["NOT", "A", "FEATURE"])
      try:
        controller.enable_feature(["NOT", "A", "FEATURE"])
      except stem.InvalidArguments, exc:
        self.assertEqual(["NOT"], exc.arguments)
      else: self.fail()
  
  def test_signal(self):
    """
    Test controller.signal with valid and invalid signals.
    """
    
    if test.runner.require_control(self): return
    
    with test.runner.get_runner().get_tor_controller() as controller:
      # valid signal
      controller.signal("CLEARDNSCACHE")
      
      # invalid signals
      self.assertRaises(stem.InvalidArguments, controller.signal, "FOOBAR")
  
  def test_extendcircuit(self):
    if test.runner.require_control(self): return
    elif test.runner.require_online(self): return
    elif test.runner.require_version(self, Requirement.EXTENDCIRCUIT_PATH_OPTIONAL): return
    
    with test.runner.get_runner().get_tor_controller() as controller:
      circuit_id = controller.extend_circuit('0')
      
      # check if our circuit was created
      self.assertIsNotNone(controller.get_circuit(circuit_id, None))
      circuit_id = controller.new_circuit()
      self.assertIsNotNone(controller.get_circuit(circuit_id, None))
      
      self.assertRaises(stem.InvalidRequest, controller.extend_circuit, "foo")
      self.assertRaises(stem.InvalidRequest, controller.extend_circuit, '0', "thisroutershouldntexistbecausestemexists!@##$%#")
      self.assertRaises(stem.InvalidRequest, controller.extend_circuit, '0', "thisroutershouldntexistbecausestemexists!@##$%#", "foo")
  
  def test_repurpose_circuit(self):
    """
    Tests Controller.repurpose_circuit with valid and invalid input.
    """
    
    if test.runner.require_control(self): return
    elif test.runner.require_online(self): return
    elif test.runner.require_version(self, Requirement.EXTENDCIRCUIT_PATH_OPTIONAL): return
    
    runner = test.runner.get_runner()
    
    with runner.get_tor_controller() as controller:
      circ_id = controller.new_circuit()
      controller.repurpose_circuit(circ_id, "CONTROLLER")
      circuit = controller.get_circuit(circ_id)
      self.assertTrue(circuit.purpose == "CONTROLLER")
      
      controller.repurpose_circuit(circ_id, "GENERAL")
      circuit = controller.get_circuit(circ_id)
      self.assertTrue(circuit.purpose == "GENERAL")
      
      self.assertRaises(stem.InvalidRequest, controller.repurpose_circuit, 'f934h9f3h4', "fooo")
      self.assertRaises(stem.InvalidRequest, controller.repurpose_circuit, '4', "fooo")
  
  def test_close_circuit(self):
    """
    Tests Controller.close_circuit with valid and invalid input.
    """
    
    if test.runner.require_control(self): return
    elif test.runner.require_online(self): return
    elif test.runner.require_version(self, Requirement.EXTENDCIRCUIT_PATH_OPTIONAL): return
    
    runner = test.runner.get_runner()
    
    with runner.get_tor_controller() as controller:
      circuit_id = controller.new_circuit()
      controller.close_circuit(circuit_id)
      circuit_output = controller.get_info("circuit-status")
      circ = [x.split()[0] for x in circuit_output.splitlines()]
      self.assertFalse(circuit_id in circ)
      
      circuit_id = controller.new_circuit()
      controller.close_circuit(circuit_id, "IfUnused")
      circuit_output = controller.get_info("circuit-status")
      circ = [x.split()[0] for x in circuit_output.splitlines()]
      self.assertFalse(circuit_id in circ)
      
      circuit_id = controller.new_circuit()
      self.assertRaises(stem.InvalidArguments, controller.close_circuit, circuit_id + "1024")
      self.assertRaises(stem.InvalidRequest, controller.close_circuit, "")
  
  def test_get_streams(self):
    """
    Tests Controller.get_streams().
    """
    
    if test.runner.require_control(self): return
    elif test.runner.require_online(self): return
    
    host = "38.229.72.14"   # www.torproject.org
    port = 443
    
    runner = test.runner.get_runner()
    with runner.get_tor_controller() as controller:
      # we only need one proxy port, so take the first
      socks_listener = controller.get_socks_listeners()[0]
      
      with test.network.Socks(socks_listener) as s:
        s.settimeout(30)
        s.connect((host, port))
        streams = controller.get_streams()
    
    # Because we do not get a stream id when opening a stream,
    #  try to match the target for which we asked a stream.
    
    self.assertTrue("%s:%s" % (host, port) in [stream.target for stream in streams])
  
  def test_close_stream(self):
    """
    Tests Controller.close_stream with valid and invalid input.
    """
    
    if test.runner.require_control(self): return
    elif test.runner.require_online(self): return
    
    runner = test.runner.get_runner()
    
    with runner.get_tor_controller() as controller:
      # use the first socks listener
      socks_listener = controller.get_socks_listeners()[0]
      with test.network.Socks(socks_listener) as s:
        s.settimeout(30)
        s.connect(("www.torproject.org", 443))
        # There's only one stream right now.  Right?
        built_stream = controller.get_streams()[0]
        # Make sure we have the stream for which we asked, otherwise
        # the next assertion would be a false positive.
        self.assertEqual([built_stream.id], [stream.id for stream in controller.get_streams()])
        # Try to close our stream...
        controller.close_stream(built_stream.id)
        # ...which means there are zero streams.
        self.assertEqual([], controller.get_streams())
      
      # unknown stream
      self.assertRaises(stem.InvalidArguments, controller.close_stream, "blarg")
  
  def test_mapaddress(self):
    if test.runner.require_control(self): return
    elif test.runner.require_online(self): return
    
    runner = test.runner.get_runner()
    
    with runner.get_tor_controller() as controller:
      controller.map_address({'1.2.1.2': 'ifconfig.me'})
      
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.connect(('127.0.0.1', int(controller.get_conf('SocksListenAddress').rsplit(':', 1)[1])))
      test.util.negotiate_socks(s, '1.2.1.2', 80)
      s.sendall(test.util.ip_request) # make the http request for the ip address
      response = s.recv(1000)
      
      # everything after the blank line is the 'data' in a HTTP response.
      # The response data for our request for request should be an IP address + '\n'
      ip_addr = response[response.find("\r\n\r\n"):].strip()
      
      self.assertTrue(stem.util.connection.is_valid_ip_address(ip_addr))
  
  def test_get_server_descriptor(self):
    """
    Compares get_server_descriptor() against our cached descriptors.
    """
    
    runner = test.runner.get_runner()
    descriptor_path = runner.get_test_dir("cached-descriptors")
    
    if test.runner.require_control(self): return
    elif not os.path.exists(descriptor_path):
      test.runner.skip(self, "(no cached descriptors)")
      return
    
    with runner.get_tor_controller() as controller:
      # we should balk at invalid content
      self.assertRaises(ValueError, controller.get_server_descriptor, None)
      self.assertRaises(ValueError, controller.get_server_descriptor, "")
      self.assertRaises(ValueError, controller.get_server_descriptor, 5)
      self.assertRaises(ValueError, controller.get_server_descriptor, "z" * 30)
      
      # try with a relay that doesn't exist
      self.assertRaises(stem.ControllerError, controller.get_server_descriptor, "blargg")
      self.assertRaises(stem.ControllerError, controller.get_server_descriptor, "5" * 40)
      
      test.runner.skip(self, "(https://trac.torproject.org/7163)")
      return
      
      first_descriptor = None
      with stem.descriptor.reader.DescriptorReader([descriptor_path]) as reader:
        for desc in reader:
          if desc.nickname != "Unnamed":
            first_descriptor = desc
            break
      
      self.assertEqual(first_descriptor, controller.get_server_descriptor(first_descriptor.fingerprint))
      self.assertEqual(first_descriptor, controller.get_server_descriptor(first_descriptor.nickname))
  
  def test_get_server_descriptors(self):
    """
    Fetches a few descriptors via the get_server_descriptors() method.
    """
    
    runner = test.runner.get_runner()
    
    if test.runner.require_control(self): return
    
    with runner.get_tor_controller() as controller:
      count = 0
      
      for desc in controller.get_server_descriptors():
        self.assertTrue(desc.fingerprint is not None)
        self.assertTrue(desc.nickname is not None)
        
        # Se don't want to take the time to read the whole thing. We already
        # have another test that reads the full cached descriptors (and takes a
        # while to do so).
        
        count += 1
        if count > 10: break
  
  def test_get_network_status(self):
    """
    Compares get_network_status() against our cached descriptors.
    """
    
    runner = test.runner.get_runner()
    descriptor_path = runner.get_test_dir("cached-consensus")
    
    if test.runner.require_control(self): return
    elif not os.path.exists(descriptor_path):
      test.runner.skip(self, "(no cached descriptors)")
      return
    
    with runner.get_tor_controller() as controller:
      # we should balk at invalid content
      self.assertRaises(ValueError, controller.get_network_status, None)
      self.assertRaises(ValueError, controller.get_network_status, "")
      self.assertRaises(ValueError, controller.get_network_status, 5)
      self.assertRaises(ValueError, controller.get_network_status, "z" * 30)
      
      # try with a relay that doesn't exist
      self.assertRaises(stem.ControllerError, controller.get_network_status, "blargg")
      self.assertRaises(stem.ControllerError, controller.get_network_status, "5" * 40)
      
      # our cached consensus is v3 but the control port can only be queried for
      # v2 or v1 network status information
      
      test.runner.skip(self, "(https://trac.torproject.org/7163)")
      return
      
      first_descriptor = None
      with stem.descriptor.reader.DescriptorReader([descriptor_path]) as reader:
        for desc in reader:
          if desc.nickname != "Unnamed":
            # truncate to just the first couple lines and reconstruct as a v2 entry
            truncated_content = "\n".join(str(desc).split("\n")[:2])
            
            first_descriptor = stem.descriptor.router_status_entry.RouterStatusEntryV2(truncated_content)
            break
      
      self.assertEqual(first_descriptor, controller.get_network_status(first_descriptor.fingerprint))
      self.assertEqual(first_descriptor, controller.get_network_status(first_descriptor.nickname))
  
  def test_get_network_statuses(self):
    """
    Fetches a few descriptors via the get_network_statuses() method.
    """
    
    runner = test.runner.get_runner()
    
    if test.runner.require_control(self): return
    
    with runner.get_tor_controller() as controller:
      count = 0
      
      for desc in controller.get_network_statuses():
        self.assertTrue(desc.fingerprint is not None)
        self.assertTrue(desc.nickname is not None)
        
        count += 1
        if count > 10: break
  
  def test_attachstream(self):
    if test.runner.require_control(self): return
    elif test.runner.require_online(self): return
    elif test.runner.require_version(self, Requirement.EXTENDCIRCUIT_PATH_OPTIONAL): return
    
    circuit_id = None
    
    def handle_streamcreated(stream):
      if stream.status == "NEW" and circuit_id:
        controller.attach_stream(stream.id, circuit_id)
    
    with test.runner.get_runner().get_tor_controller() as controller:
      controller.set_conf("__LeaveStreamsUnattached", "1")
      controller.add_event_listener(handle_streamcreated, stem.control.EventType.STREAM)
      
      try:
        circuit_id = controller.new_circuit(await_build = True)
        socksport = controller.get_socks_listeners()[0][1]
        
        ip = test.util.external_ip('127.0.0.1', socksport)
        exit_circuit = controller.get_circuit(circuit_id)
        self.assertTrue(exit_circuit)
        exit_ip = controller.get_network_status(exit_circuit.path[2][0]).address
        
        self.assertEquals(exit_ip, ip)
      finally:
        controller.remove_event_listener(handle_streamcreated)
        controller.reset_conf("__LeaveStreamsUnattached")
  
  def test_get_circuits(self):
    """
    Fetches circuits via the get_circuits() method.
    """
    
    if test.runner.require_control(self): return
    elif test.runner.require_online(self): return
    elif test.runner.require_version(self, Requirement.EXTENDCIRCUIT_PATH_OPTIONAL): return
    
    runner = test.runner.get_runner()
    with runner.get_tor_controller() as controller:
      new_circ = controller.new_circuit()
      circuits = controller.get_circuits()
      self.assertTrue(new_circ in [circ.id for circ in circuits])

