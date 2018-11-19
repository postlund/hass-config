#!/usr/bin/env python3

import asyncio
from datetime import timedelta

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
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity import Entity
from homeassistant.core import callback
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST
from homeassistant.helpers.dispatcher import (
    async_dispatcher_send, async_dispatcher_connect)
from homeassistant.helpers import discovery
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util.dt import utcnow
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.media_player import (
    MEDIA_TYPE_VIDEO, ATTR_MEDIA_CONTENT_ID, ATTR_MEDIA_CONTENT_TYPE,
    SERVICE_PLAY_MEDIA)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

DOMAIN = 'media_watcher'
REQUIREMENTS = ['plexapi==3.0.0']
_LOGGER = logging.getLogger(__name__)

ATTR_SECTION = 'section'

SERVICE_LATEST_IN_SECTION = 'latest_in_section'

CONF_SECTION_COUNT = 'section_count'
CONF_TV_SHOWS = 'tv_shows'
CONF_SECTIONS = 'sections'

SIGNAL_UPDATE_DATA = 'media_watcher_update'

SCAN_INTERVAL = timedelta(seconds=60)

MEDIA_WATCHER_SECTION_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.entity_id,
    ATTR_SECTION: cv.string,
})


CONFIG_SCHEMA = vol.Schema({
    vol.Required(DOMAIN): vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_SECTION_COUNT, default=5): cv.positive_int,
        vol.Optional(CONF_TV_SHOWS, default=[]):
            vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_SECTIONS, default=[]):
            vol.All(cv.ensure_list, [cv.string])
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
    """Setup media watcher component."""
    domain = config[DOMAIN]
    section_count = domain[CONF_SECTION_COUNT]

    watcher = MediaWatcher(hass, domain[CONF_HOST])
    hass.data['media_watcher'] = watcher

    @asyncio.coroutine
    def async_update_data(now):
        for section in domain[CONF_SECTIONS]:
            yield from watcher.async_update_latest_in_section(
                section, section_count)

        for tv_show in domain[CONF_TV_SHOWS]:
            yield from watcher.async_search(tv_show)

        async_dispatcher_send(hass, SIGNAL_UPDATE_DATA)
        async_track_point_in_utc_time(
            hass, async_update_data, utcnow() + SCAN_INTERVAL)

    @asyncio.coroutine
    def async_handle_latest_section(service):
        section = service.data[ATTR_SECTION]
        yield from watcher.async_update_latest_in_section(
            section, section_count)

    hass.services.async_register(
        DOMAIN, SERVICE_LATEST_IN_SECTION, async_handle_latest_section,
        None, schema=MEDIA_WATCHER_SECTION_SCHEMA)

    yield from async_update_data(None)

    for title in watcher.searches:
        hass.async_add_job(discovery.async_load_platform(
                hass, 'sensor', 'media_watcher', {
                    'title': title,
                    }, config))

    for section in watcher.sections:
        for index in range(section_count):
            hass.async_add_job(discovery.async_load_platform(
                    hass, 'sensor', 'media_watcher', {
                        'section': section,
                        'index': index
                        }, config))

    return True


class MediaWatcher:

    def __init__(self, hass, server):
        self._hass = hass
        self._server = server
        self.sections = {}
        self.searches = {}

    @asyncio.coroutine
    def async_search(self, search_term):
        def _do_search():
            from plexapi.server import PlexServer
            plex = PlexServer(self._server, None)

            matches = plex.search(search_term)
            if matches:
                match = matches[0]
                self.searches[match.title] = match.unwatched()
            else:
                _LOGGER.warning('No matches for %s', search_term)

        return self._hass.loop.run_in_executor(None, _do_search)

    @asyncio.coroutine
    def async_update_latest_in_section(self, section, count):
        latest = yield from self._hass.loop.run_in_executor(
            None, self.get_latest, section, count)
        self.sections[section] = latest

    def get_latest(self, section, count):
        from plexapi.server import PlexServer
        plex = PlexServer(self._server, None)
        entries = plex.library.section(
            self._lookup_section(plex, section)).recentlyAdded()
        return self._get_latest_unwatched(entries, count)

    def _lookup_section(self, plex, section):
        for plex_section in plex.library.sections():
            if plex_section.title.lower() == section.lower():
                return plex_section.title
        return section

    def _get_latest_unwatched(self, entries, count):
        items = list(filter(lambda x: not x.isWatched, entries))
        items.sort(key=lambda x: x.addedAt)
        return items[-count:]
