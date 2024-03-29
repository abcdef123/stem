"""
Unit tests for the stem.response.protocolinfo.ProtocolInfoResponse class.
"""

import os
import unittest

import stem.response
import stem.response.protocolinfo
import stem.socket
import stem.util.proc
import stem.util.system
import stem.version

from stem.response.protocolinfo import AuthMethod
from test import mocking

NO_AUTH = """250-PROTOCOLINFO 1
250-AUTH METHODS=NULL
250-VERSION Tor="0.2.1.30"
250 OK"""

PASSWORD_AUTH = """250-PROTOCOLINFO 1
250-AUTH METHODS=HASHEDPASSWORD
250-VERSION Tor="0.2.1.30"
250 OK"""

COOKIE_AUTH = r"""250-PROTOCOLINFO 1
250-AUTH METHODS=COOKIE COOKIEFILE="/tmp/my data\\\"dir//control_auth_cookie"
250-VERSION Tor="0.2.1.30"
250 OK"""

MULTIPLE_AUTH = """250-PROTOCOLINFO 1
250-AUTH METHODS=COOKIE,HASHEDPASSWORD COOKIEFILE="/home/atagar/.tor/control_auth_cookie"
250-VERSION Tor="0.2.1.30"
250 OK"""

UNKNOWN_AUTH = """250-PROTOCOLINFO 1
250-AUTH METHODS=MAGIC,HASHEDPASSWORD,PIXIE_DUST
250-VERSION Tor="0.2.1.30"
250 OK"""

MINIMUM_RESPONSE = """250-PROTOCOLINFO 5
250 OK"""

RELATIVE_COOKIE_PATH = r"""250-PROTOCOLINFO 1
250-AUTH METHODS=COOKIE COOKIEFILE="./tor-browser_en-US/Data/control_auth_cookie"
250-VERSION Tor="0.2.1.30"
250 OK"""

class TestProtocolInfoResponse(unittest.TestCase):
  def test_convert(self):
    """
    Exercises functionality of the convert method both when it works and
    there's an error.
    """
    
    # working case
    control_message = mocking.get_message(NO_AUTH)
    stem.response.convert("PROTOCOLINFO", control_message)
    
    # now this should be a ProtocolInfoResponse (ControlMessage subclass)
    self.assertTrue(isinstance(control_message, stem.response.ControlMessage))
    self.assertTrue(isinstance(control_message, stem.response.protocolinfo.ProtocolInfoResponse))
    
    # exercise some of the ControlMessage functionality
    raw_content = (NO_AUTH + "\n").replace("\n", "\r\n")
    self.assertEquals(raw_content, control_message.raw_content())
    self.assertTrue(str(control_message).startswith("PROTOCOLINFO 1"))
    
    # attempt to convert the wrong type
    self.assertRaises(TypeError, stem.response.convert, "PROTOCOLINFO", "hello world")
    
    # attempt to convert a different message type
    bw_event_control_message = mocking.get_message("650 BW 32326 2856")
    self.assertRaises(stem.ProtocolError, stem.response.convert, "PROTOCOLINFO", bw_event_control_message)
  
  def test_no_auth(self):
    """
    Checks a response when there's no authentication.
    """
    
    control_message = mocking.get_message(NO_AUTH)
    stem.response.convert("PROTOCOLINFO", control_message)
    
    self.assertEquals(1, control_message.protocol_version)
    self.assertEquals(stem.version.Version("0.2.1.30"), control_message.tor_version)
    self.assertEquals((AuthMethod.NONE, ), control_message.auth_methods)
    self.assertEquals((), control_message.unknown_auth_methods)
    self.assertEquals(None, control_message.cookie_path)
  
  def test_password_auth(self):
    """
    Checks a response with password authentication.
    """
    
    control_message = mocking.get_message(PASSWORD_AUTH)
    stem.response.convert("PROTOCOLINFO", control_message)
    self.assertEquals((AuthMethod.PASSWORD, ), control_message.auth_methods)
  
  def test_cookie_auth(self):
    """
    Checks a response with cookie authentication and a path including escape
    characters.
    """
    
    control_message = mocking.get_message(COOKIE_AUTH)
    stem.response.convert("PROTOCOLINFO", control_message)
    self.assertEquals((AuthMethod.COOKIE, ), control_message.auth_methods)
    self.assertEquals("/tmp/my data\\\"dir//control_auth_cookie", control_message.cookie_path)
  
  def test_multiple_auth(self):
    """
    Checks a response with multiple authentication methods.
    """
    
    control_message = mocking.get_message(MULTIPLE_AUTH)
    stem.response.convert("PROTOCOLINFO", control_message)
    self.assertEquals((AuthMethod.COOKIE, AuthMethod.PASSWORD), control_message.auth_methods)
    self.assertEquals("/home/atagar/.tor/control_auth_cookie", control_message.cookie_path)
  
  def test_unknown_auth(self):
    """
    Checks a response with an unrecognized authtentication method.
    """
    
    control_message = mocking.get_message(UNKNOWN_AUTH)
    stem.response.convert("PROTOCOLINFO", control_message)
    self.assertEquals((AuthMethod.UNKNOWN, AuthMethod.PASSWORD), control_message.auth_methods)
    self.assertEquals(("MAGIC", "PIXIE_DUST"), control_message.unknown_auth_methods)
  
  def test_minimum_response(self):
    """
    Checks a PROTOCOLINFO response that only contains the minimum amount of
    information to be a valid response.
    """
    
    control_message = mocking.get_message(MINIMUM_RESPONSE)
    stem.response.convert("PROTOCOLINFO", control_message)
    
    self.assertEquals(5, control_message.protocol_version)
    self.assertEquals(None , control_message.tor_version)
    self.assertEquals((), control_message.auth_methods)
    self.assertEquals((), control_message.unknown_auth_methods)
    self.assertEquals(None, control_message.cookie_path)
  
  def test_relative_cookie(self):
    """
    Checks an authentication cookie with a relative path where expansion both
    succeeds and fails.
    """
    
    # TODO: move into stem.connection unit tests?
    
    # we need to mock both pid and cwd lookups since the general cookie
    # expanion works by...
    # - resolving the pid of the "tor" process
    # - using that to get tor's cwd
    
    def call_mocking(command):
      if command == stem.util.system.GET_PID_BY_NAME_PGREP % "tor":
        return ["10"]
      elif command == stem.util.system.GET_CWD_PWDX % 10:
        return ["10: /tmp/foo"]
    
    mocking.mock(stem.util.proc.is_available, mocking.return_false())
    mocking.mock(stem.util.system.is_available, mocking.return_true())
    mocking.mock(stem.util.system.call, call_mocking)
    
    control_message = mocking.get_message(RELATIVE_COOKIE_PATH)
    stem.response.convert("PROTOCOLINFO", control_message)
    
    stem.connection._expand_cookie_path(control_message, stem.util.system.get_pid_by_name, "tor")
    
    self.assertEquals(os.path.join("/tmp/foo", "tor-browser_en-US", "Data", "control_auth_cookie"), control_message.cookie_path)
    
    # exercise cookie expansion where both calls fail (should work, just
    # leaving the path unexpanded)
    
    mocking.mock(stem.util.system.call, mocking.return_none())
    control_message = mocking.get_message(RELATIVE_COOKIE_PATH)
    stem.response.convert("PROTOCOLINFO", control_message)
    self.assertEquals("./tor-browser_en-US/Data/control_auth_cookie", control_message.cookie_path)
    
    # reset system call mocking
    mocking.revert_mocking()

