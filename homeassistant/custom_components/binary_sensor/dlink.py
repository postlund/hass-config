#!/usr/bin/env python3
"""Read data from D-Link motion sensor."""

import xml
import hmac
import urllib
import logging
import asyncio
import functools
from datetime import datetime

from pysimplesoap.client import SoapClient

_LOGGER = logging.getLogger(__name__)

NAMESPACE = 'http://purenetworks.com/HNAP1/'
ACTION_BASE_URL = 'http://purenetworks.com/HNAP1/'


def _hmac(key, message):
    return hmac.new(key.encode('utf-8'),
                    message.encode('utf-8')).hexdigest().upper()


class AuthenticationError(Exception):
    """Thrown when login fails."""

    pass


class HNAPClient:
    """Client for the HNAP protocol."""

    def __init__(self, address, username, password, loop=None):
        """Initialize a new HNAPClient instance."""
        self.address = address
        self.username = username
        self.password = password
        self.logged_in = False
        self.loop = loop or asyncio.get_event_loop()
        self.actions = None
        self._private_key = None
        self._cookie = None
        self._auth_token = None
        self._timestamp = None

    @asyncio.coroutine
    def login(self):
        """Authenticate with device and obtain cookie."""
        self.logged_in = False
        resp = yield from self.call(
            'Login', Action='request', Username=self.username,
            LoginPassword='', Captcha='')

        challenge = str(resp.LoginResponse.Challenge)
        public_key = str(resp.LoginResponse.PublicKey)
        self._cookie = str(resp.LoginResponse.Cookie)
        _LOGGER.debug('Challenge: %s, Public key: %s, Cookie: %s',
                      challenge, public_key, self._cookie)

        self._private_key = _hmac(public_key + str(self.password), challenge)
        _LOGGER.debug('Private key: %s', self._private_key)

        try:
            password = _hmac(self._private_key, challenge)
            resp = yield from self.call(
                'Login', Action='login', Username=self.username,
                LoginPassword=password, Captcha='')

            if str(resp.LoginResult).lower() != 'success':
                raise AuthenticationError('Incorrect username or password')

            if not self.actions:
                self.actions = yield from self.device_actions()

        except xml.parsers.expat.ExpatError:
            raise AuthenticationError('Bad response from device')

        self.logged_in = True

    @asyncio.coroutine
    def device_actions(self):
        def _extract(action):
            url = str(action)
            return url[url.rfind('/')+1:]
        actions = yield from self.call('GetDeviceSettings')
        return list(map(_extract, actions.SOAPActions.children()))

    @asyncio.coroutine
    def call(self, method, *args, **kwargs):
        """Call an NHAP method (async)."""
        def _call_method():
            self._update_nauth_token(method)
            method_to_call = getattr(self._client(), method)
            return self.loop.run_in_executor(
                None, functools.partial(method_to_call, *args, **kwargs))

        # Do login if no login has been done before
        if not self._private_key and method != 'Login':
            yield from self.login()

        try:
            res = yield from _call_method()

            # Force login if if we a HTTP page (it's likely Unauthorized)
            if 'body' not in res:
                return res

        except AttributeError:
            _LOGGER.debug('Got logged out, logging in again')
        except xml.parsers.expat.ExpatError:
            _LOGGER.debug('Got logged out, logging in again')
        except urllib.error.HTTPError:
            _LOGGER.debug('Got logged out, logging in again')
        except urllib.error.URLError:
            _LOGGER.debug('Timed out')
        yield from self.login()
        return (yield from _call_method())

    def _update_nauth_token(self, action):
        """Update NHAP auth token for an action."""
        if not self._private_key:
            return

        self._timestamp = int(datetime.now().timestamp())
        self._auth_token = _hmac(
            self._private_key,
            '{0}"{1}{2}"'.format(self._timestamp, ACTION_BASE_URL, action))
        _LOGGER.debug('Generated new token for %s: %s (time: %d)',
                      action, self._auth_token, self._timestamp)

    def _client(self):
        headers = {}

        if self._cookie:
            headers['Cookie'] = 'uid={0}'.format(self._cookie)
        if self._auth_token:
            headers['HNAP_AUTH'] = '{0} {1}'.format(
                self._auth_token, self._timestamp)

        client = SoapClient(
            'http://{0}/HNAP1'.format(self.address), trace=True,
            namespace=NAMESPACE,
            action=ACTION_BASE_URL,
            http_headers=headers)

        # The device is very picky about the request and will fail if an empty
        # Header-tag is included. Unfortunately, it's not possible to remove
        # that tag from pysimplesoap without modifying the library. This is a
        # hack that modifies the internal request and removes the header. Not
        # pretty, but will have to do for now. Over and out.
        # pylint: disable=protected-access
        client._SoapClient__xml = client._SoapClient__xml.replace(
            '<%(soap_ns)s:Header/>\n', '')
        return client


class MotionSensor:
    """Wrapper class for a motion sensor."""

    def __init__(self, client):
        """Initialize a new MotionSensor instance."""
        self.client = client

    @asyncio.coroutine
    def latest_trigger(self):
        """Get latest trigger time from sensor."""
        resp = yield from self.client.call(
            'GetMotionDetectorLogs', ModuleID=1, MaxCount=1,
            PageOffset=1, StartTime=0, EndTime='All')

        log_list = resp.MotionDetectorLogList
        return datetime.fromtimestamp(float(log_list[0].TimeStamp))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    import sys
    address = sys.argv[1]
    pin = sys.argv[2]
    cmd = sys.argv[3]

    @asyncio.coroutine
    def _print_latest_motion():
        client = HNAPClient(address, 'Admin', pin, loop=loop)
        motion = MotionSensor(client)
        yield from client.login()

        if cmd == 'latest_motion':
            latest = yield from motion.latest_trigger()
            print('Latest time: ' + str(latest))
        elif cmd == 'actions':
            print('Supported actions:')
            print('\n'.join(client.actions))

    loop.run_until_complete(_print_latest_motion())
