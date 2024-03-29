"""
Unit tests for the stem.connection.authenticate function.

Under the covers the authentiate function really just translates a
PROTOCOLINFO response into authenticate_* calls, then does prioritization
on the exceptions if they all fail.

This monkey patches the various functions authenticate relies on to exercise
various error conditions, and make sure that the right exception is raised.
"""

import unittest

import stem.connection

from stem.util import log
from test import mocking

class TestAuthenticate(unittest.TestCase):
  def setUp(self):
    mocking.mock(stem.connection.get_protocolinfo, mocking.no_op())
    mocking.mock(stem.connection.authenticate_none, mocking.no_op())
    mocking.mock(stem.connection.authenticate_password, mocking.no_op())
    mocking.mock(stem.connection.authenticate_cookie, mocking.no_op())
    mocking.mock(stem.connection.authenticate_safecookie, mocking.no_op())
  
  def tearDown(self):
    mocking.revert_mocking()
  
  def test_with_get_protocolinfo(self):
    """
    Tests the authenticate() function when it needs to make a get_protocolinfo.
    """
    
    # tests where get_protocolinfo succeeds
    protocolinfo_response = mocking.get_protocolinfo_response(
      auth_methods = (stem.connection.AuthMethod.NONE, ),
    )
    
    mocking.mock(stem.connection.get_protocolinfo, mocking.return_value(protocolinfo_response))
    stem.connection.authenticate(None)
    
    # tests where get_protocolinfo raises an exception
    raised_exc = stem.ProtocolError(None)
    mocking.mock(stem.connection.get_protocolinfo, mocking.raise_exception(raised_exc))
    self.assertRaises(stem.connection.IncorrectSocketType, stem.connection.authenticate, None)
    
    raised_exc = stem.SocketError(None)
    mocking.mock(stem.connection.get_protocolinfo, mocking.raise_exception(raised_exc))
    self.assertRaises(stem.connection.AuthenticationFailure, stem.connection.authenticate, None)
  
  def test_all_use_cases(self):
    """
    Does basic validation that all valid use cases for the PROTOCOLINFO input
    and dependent functions result in either success or a AuthenticationFailed
    subclass being raised.
    """
    
    # mute the logger for this test since otherwise the output is overwhelming
    
    stem_logger = log.get_logger()
    stem_logger.setLevel(log.logging_level(None))
    
    # exceptions that the authentication functions are documented to raise
    all_auth_none_exc = (None,
      stem.connection.OpenAuthRejected(None))
    
    all_auth_password_exc = (None,
      stem.connection.PasswordAuthRejected(None),
      stem.connection.IncorrectPassword(None))
    
    all_auth_cookie_exc = (None,
      stem.connection.IncorrectCookieSize(None, False, None),
      stem.connection.UnreadableCookieFile(None, False, None),
      stem.connection.CookieAuthRejected(None, False, None),
      stem.connection.IncorrectCookieValue(None, False, None),
      stem.connection.UnrecognizedAuthChallengeMethod(None, None, None),
      stem.connection.AuthChallengeFailed(None, None),
      stem.connection.AuthSecurityFailure(None, None),
      stem.connection.InvalidClientNonce(None, None))
    
    # authentication functions might raise a controller error when
    # 'suppress_ctl_errors' is False, so including those
    
    control_exc = (
      stem.ProtocolError(None),
      stem.SocketError(None),
      stem.SocketClosed(None))
    
    all_auth_none_exc += control_exc
    all_auth_password_exc += control_exc
    all_auth_cookie_exc += control_exc
    
    auth_method_combinations = mocking.get_all_combinations([
      stem.connection.AuthMethod.NONE,
      stem.connection.AuthMethod.PASSWORD,
      stem.connection.AuthMethod.COOKIE,
      stem.connection.AuthMethod.SAFECOOKIE,
      stem.connection.AuthMethod.UNKNOWN,
    ], include_empty = True)
    
    for protocolinfo_auth_methods in auth_method_combinations:
      # protocolinfo input for the authenticate() call we'll be making
      protocolinfo_arg = mocking.get_protocolinfo_response(
        auth_methods = protocolinfo_auth_methods,
        cookie_path = "/tmp/blah",
      )
      
      for auth_none_exc in all_auth_none_exc:
        for auth_password_exc in all_auth_password_exc:
          for auth_cookie_exc in all_auth_cookie_exc:
            # Determine if the authenticate() call will succeed and mock each
            # of the authenticate_* function to raise its given exception.
            #
            # This implementation is slightly inaccurate in a couple regards...
            # a. it raises safecookie exceptions from authenticate_cookie()
            # b. exceptions raised by authenticate_cookie() and
            #    authenticate_safecookie() are always the same
            #
            # However, adding another loop for safe_cookie exceptions means
            # multiplying our runtime many fold. This exercises everything that
            # matters so the above inaccuracies seem fine.
            
            expect_success = False
            auth_mocks = {
              stem.connection.AuthMethod.NONE:
                (stem.connection.authenticate_none, auth_none_exc),
              stem.connection.AuthMethod.PASSWORD:
                (stem.connection.authenticate_password, auth_password_exc),
              stem.connection.AuthMethod.COOKIE:
                (stem.connection.authenticate_cookie, auth_cookie_exc),
              stem.connection.AuthMethod.SAFECOOKIE:
                (stem.connection.authenticate_safecookie, auth_cookie_exc),
            }
            
            for auth_method in auth_mocks:
              auth_function, raised_exc = auth_mocks[auth_method]
              
              if not raised_exc:
                # Mocking this authentication method so it will succeed. If
                # it's among the protocolinfo methods then expect success.
                
                mocking.mock(auth_function, mocking.no_op())
                expect_success |= auth_method in protocolinfo_auth_methods
              else:
                mocking.mock(auth_function, mocking.raise_exception(raised_exc))
            
            if expect_success:
              stem.connection.authenticate(None, "blah", None, protocolinfo_arg)
            else:
              self.assertRaises(stem.connection.AuthenticationFailure, stem.connection.authenticate, None, "blah", None, protocolinfo_arg)
    
    # revert logging back to normal
    stem_logger.setLevel(log.logging_level(log.TRACE))

