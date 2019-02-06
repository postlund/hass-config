#!/usr/bin/env python3

import asyncio

import aiohttp
import async_timeout

import json
import re
import sys
import logging
import urllib.request
import xml.etree.ElementTree as ET

import voluptuous as vol

from homeassistant.components import media_player
import homeassistant.helpers.config_validation as cv

from homeassistant.util import slugify
from homeassistant.helpers.entity import Entity
from homeassistant.core import callback
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.media_player import (
    MEDIA_TYPE_VIDEO, ATTR_MEDIA_CONTENT_ID, ATTR_MEDIA_CONTENT_TYPE,
    SERVICE_PLAY_MEDIA)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

DOMAIN = 'svtplay_dl'

REQUIREMENTS = ['svtplay_dl==2.0']

_LOGGER = logging.getLogger(__name__)

ATTR_ACCOUNT = 'account'
ATTR_URL = 'url'
ATTR_LIVE = 'live'
ATTR_TITLE = 'title'

SERVICE_PLAY_URL = 'play_url'

CONF_ACCOUNTS = 'accounts'

CONF_USERNAME = 'username'
CONF_PASSWORD = 'password'

PLAY_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.entity_id,
    ATTR_ACCOUNT: cv.string,
    ATTR_URL: cv.string,
    ATTR_TITLE: cv.string,
    ATTR_LIVE: cv.boolean
})


CONFIG_SCHEMA = vol.Schema({
    vol.Required(DOMAIN): vol.Schema({
        vol.Optional(CONF_ACCOUNTS): vol.Schema({
             cv.slug: vol.Any({
                 vol.Required(CONF_USERNAME): cv.string,
                 vol.Required(CONF_PASSWORD): cv.string,
             })
        }),
    }),
}, extra=vol.ALLOW_EXTRA)


@asyncio.coroutine
def get_url(hass, url):
    websession = async_get_clientsession(hass)
    request = None
    try:
        with async_timeout.timeout(10, loop=hass.loop):
            request = yield from websession.get(url)

            if request.status != 200:
                _LOGGER.error("Error %d on load url %s",
                              request.status, request.url)
                return None

            return (yield from request.read())

    except (asyncio.TimeoutError, aiohttp.errors.ClientError):
        _LOGGER.error('Timeout downloading url.')

    finally:
        if request is not None:
            yield from request.release()

    return None


def play_url(hass, account, url, entity_id, title=None, live=False):
    hass.add_job(async_play_url, account, url, entity_id, title, live)


@callback
def async_play_url(hass, account, url, entity_id, title=None, live=False):
    data = {
        ATTR_ENTITY_ID: entity_id,
        ATTR_URL: url,
        ATTR_ACCOUNT: account,
        ATTR_TITLE: title,
        ATTR_LIVE: live
    }
    hass.async_add_job(hass.services.async_call(DOMAIN, SERVICE_PLAY_URL, data))


@asyncio.coroutine
def async_setup(hass, config):
    """Setup example component."""
    domain = config[DOMAIN]

    entity = SvtPlayEntity(hass, 'Link')

    @asyncio.coroutine
    def async_handle_play(service):
        account = service.data[ATTR_ACCOUNT]
        if not account in domain[CONF_ACCOUNTS]:
            _LOGGER.warning('missing account ' + account)
            return

        username = domain[CONF_ACCOUNTS][account][CONF_USERNAME]
        password = domain[CONF_ACCOUNTS][account][CONF_PASSWORD]
        url = service.data[ATTR_URL]

        player = Svtplay(hass, entity, username, password,
                         service.data[ATTR_ENTITY_ID],
                         url,
                         service.data[ATTR_LIVE])
        try:
            if url == ('!'):
                res = (yield from player.async_feed(service.data[ATTR_TITLE]))
            else:
                res = (yield from player.async_play())
        except Exception as ex:
            _LOGGER.error('Failed to play: %s', ex)
            res = False

        entity.set_state(player._url if res else None)

    hass.services.async_register(
        DOMAIN, SERVICE_PLAY_URL, async_handle_play, schema=PLAY_SCHEMA)

    return True


class Svtplay:

    def __init__(self, hass, entity, username, password, entity_id, url, live):
        self._hass = hass
        self._entity = entity
        self._username = username
        self._password = password
        self._entity_id = entity_id
        self._url = url
        self._live = live

    @asyncio.coroutine
    def async_feed(self, title):
        js = yield from get_url(self._hass, 'http://webapi.tv4play.se/play/video_assets?nodes=' + title)
        data = json.loads(js.decode('utf-8'))

        if data['total_hits'] == 0:
            _LOGGER.warning('No program found')
            return False

        program = data['results'][0]
        self._url = 'http://www.tv4play.se/program/{0}?video_id={1}'.format(
            program['program_nid'], program['id'])

        _LOGGER.info('Found URL: ' + self._url)
        return (yield from self.async_play())

    @asyncio.coroutine
    def async_play(self):
        _LOGGER.warning('Trying to play %s', self._url)
        cmd = self._build_cmd(add_account=False)
        proc = yield from asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        (stdout, stderr) = yield from proc.communicate()

        if proc.returncode == 0 and len(stderr) == 0:
            url = stdout.decode('utf-8').strip('\n')
            if url.startswith('https://'):
                return (yield from self.async_play_url(url))
            else:
                _LOGGER.warning('Got invalid response: %s', url)
        elif self._live:
            return (yield from self.async_live_stream(stderr.decode('utf-8')))

        return False

    def _build_cmd(self, add_account=True):
        cmd = ['/srv/homeassistant/bin/svtplay-dl', '-g']
        if add_account:
            cmd.append('-u')
            cmd.append(self._username)
            cmd.append('-p')
            cmd.append(self._password)
        if self._live:
            cmd.append('-l')
            cmd.append('-P')
            cmd.append('rtmp')
            cmd.append('-v')
        cmd.append(self._url)
        return ' '.join(cmd)

    @asyncio.coroutine
    def async_play_url(self, url):
        _LOGGER.info('Starting to play %s at %s', url, self._entity_id)
        data = {
            ATTR_ENTITY_ID: self._entity_id,
            ATTR_MEDIA_CONTENT_ID: url,
            ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_VIDEO
        }

        self._hass.async_add_job(self._hass.services.async_call(
            media_player.DOMAIN, SERVICE_PLAY_MEDIA, data))
        return True

    @asyncio.coroutine
    def async_live_stream(self, output):
        metafile = re.findall(r"HTTP getting '(.*)'\n$", output)
        if len(metafile) == 0:
            _LOGGER.warning('No link found for %s', self._url)
            _LOGGER.warning("output: %s", output)
            return

        websession = async_get_clientsession(self._hass)
        request = None
        try:
            with async_timeout.timeout(10, loop=self._hass.loop):
                request = yield from websession.get(metafile[0])

                if request.status != 200:
                    _LOGGER.error("Error %d on load url %s",
                                  request.status, request.url)
                    return

                data = yield from request.read()
                root = ET.fromstring(data)
                nodes = root.findall('.//url')
                if len(nodes) > 0:
                    return (yield from self.async_play_url(nodes[0].text))
                else:
                    _LOGGER.error('no url')
        except (asyncio.TimeoutError, aiohttp.errors.ClientError):
            _LOGGER.error("Timeout.")

        finally:
            if request is not None:
                yield from request.release()

        return False

class SvtPlayEntity(Entity):

    def __init__(self, hass, name):
        """Initialize the link."""
        self.hass = hass
        self._name = name
        self._state = None
        self.entity_id = DOMAIN + '.%s' % slugify(name)
        self.schedule_update_ha_state()

    def set_state(self, state):
        self._state = state
        self.schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of the URL."""
        return self._name

    @property
    def state(self):
        """Return the URL."""
        return self._state

    @property
    def should_poll(self):
        """Polling is not needed."""
        return False

