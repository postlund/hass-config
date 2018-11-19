#!/usr/bin/env python3

import asyncio

import aiohttp
import async_timeout

import sys
import logging
import subprocess
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

DOMAIN = 'plex'
REQUIREMENTS = ['plexapi==2.0.2']
_LOGGER = logging.getLogger(__name__)

ATTR_SECTION = 'section'

SERVICE_LATEST_IN_SECTION = 'latest_in_section'

CONF_SERVER = 'server'

PLEX_SECTION_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.entity_id,
    ATTR_SECTION: cv.string,
})


CONFIG_SCHEMA = vol.Schema({
    vol.Required(DOMAIN): vol.Schema({
        vol.Required(CONF_SERVER): cv.string,

    }),
}, extra=vol.ALLOW_EXTRA)


def latest_in_section(hass, section, title=None):
    hass.add_job(async_latest_in_section, section, title)

def async_latest_in_section(hass, section, title=None):
    data = {
        ATTR_SECTION: section,
    }
    hass.async_add_job(hass.services.async_call(
            DOMAIN, SERVICE_LATEST_IN_SECTION, data))

@asyncio.coroutine
def async_setup(hass, config):
    """Setup example component."""
    domain = config[DOMAIN]

    plex_entity = PlexEntity(hass, 'Section')

    @asyncio.coroutine
    def async_handle_latest_section(service):
        section = service.data[ATTR_SECTION]
        plex = PlexPlayer(hass, domain[CONF_SERVER], plex_entity)
        yield from plex.async_update_latest_in_section(section)

    hass.services.async_register(
        DOMAIN, SERVICE_LATEST_IN_SECTION, async_handle_latest_section,
        schema=PLEX_SECTION_SCHEMA)

    return True

class PlexEntity(Entity):

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


class PlexPlayer:

    def __init__(self, hass, server, entity):
        self._hass = hass
        self._server = server
        self._entity = entity

    @asyncio.coroutine
    def async_update_latest_in_section(self, section):
        latest = yield from self.async_get_latest_in_section(section)

        items = []
        for item in latest:
            if item.type == 'episode':
                items.append(item.show().title + ' - ' + item.title)
            else:
                items.append(item.title)

        str = ', '.join(items[:-1]) + ' - and - ' + items[-1]
        self._entity.set_state(str)

    @asyncio.coroutine
    def async_get_latest_in_section(self, section):
        return self._hass.loop.run_in_executor(
            None, self.get_latest, section, 4)

    def get_latest(self, section, count):
        from plexapi.server import PlexServer
        plex = PlexServer(self._server, None)
        entries = plex.library.section(
            self.lookup_section(plex, section)).recentlyAdded()
        return self.get_latest_unwatched(entries, count)

    def lookup_section(self, plex, section):
        for plex_section in plex.library.sections():
            if plex_section.title.lower() == section.lower():
                return plex_section.title
        return section

    def get_latest_unwatched(self, entries, count):
        items = []
        for m in entries:
            if not m.isWatched:
                items.append(m)

        items.sort(key=lambda x: x.addedAt)
        return items[-count:]
