# TODO: show() blocks the event loop
import asyncio

from homeassistant.util import slugify
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import (
    async_dispatcher_send, async_dispatcher_connect)
from custom_components.media_watcher import SIGNAL_UPDATE_DATA

DEPENDENCIES = ['media_watcher']


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up media watcher Sensor."""
    if discovery_info is None:
        return

    watcher = hass.data['media_watcher']

    # Hack for now...
    if 'title' in discovery_info:
        title = discovery_info['title']
        async_add_devices([TvSeriesSensor(hass, watcher, title)])
    else:
        section = discovery_info['section']
        index = discovery_info['index']
        async_add_devices([SectionSensor(hass, watcher, section, index)])


class TvSeriesSensor(Entity):

    def __init__(self, hass, watcher, title):
        """Initialize the TV series sensor."""
        self.hass = hass
        self.watcher = watcher
        self.title = title
        self._no_unwatched = 0

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Register update dispatcher."""
        self._no_unwatched = len(self.watcher.searches[self.title])

        @callback
        def async_update():
            """Update callback."""
            unwatched = len(self.watcher.searches[self.title])

            if unwatched != self._no_unwatched:
                self._no_unwatched = unwatched
                self.hass.async_add_job(self.async_update_ha_state(True))

        async_dispatcher_connect(
            self.hass, SIGNAL_UPDATE_DATA, async_update)

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return self.title

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._no_unwatched

    @property
    def should_poll(self):
        """Polling is not needed."""
        return False

    @property
    def available(self):
        """Return True if entity is available."""
        return self.title in self.watcher.searches

    @property
    def hidden(self):
        """Return True if the entity should be hidden from UIs."""
        return self._no_unwatched == 0

    @property
    def icon(self):
        """Return the default icon of the sensor."""
        return 'mdi:television'


class SectionSensor(Entity):

    def __init__(self, hass, watcher, section, index):
        """Initialize the section sensor."""
        self.hass = hass
        self.watcher = watcher
        self.section = section
        self.index = index
        self.entity_id = ENTITY_ID_FORMAT.format(slugify(section + '_' + str(index)))
        self._latest_item = None

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Register update dispatcher."""
        self._latest_item = self.watcher.sections[self.section][self.index]

        @callback
        def async_update():
            """Update callback."""
            latest = self.watcher.sections[self.section][self.index]

            if latest != self._latest_item:
                self._latest_item = latest
                self.hass.async_add_job(self.async_update_ha_state(True))

        async_dispatcher_connect(
            self.hass, SIGNAL_UPDATE_DATA, async_update)

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        if self._latest_item.type == 'episode':
            return self._latest_item.show().title
        else:
            return self.section

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._latest_item.title

    @property
    def should_poll(self):
        """Polling is not needed."""
        return False

    @property
    def available(self):
        """Return True if entity is available."""
        return self.section in self.watcher.sections

    @property
    def hidden(self):
        """Return True if the entity should be hidden from UIs."""
        return not self._latest_item

    @property
    def icon(self):
        """Return the default icon of the sensor."""
        return 'mdi:movie'

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        if self.available:
            genres = self._latest_item.genres or []
            attributes = {
                'year': self._latest_item.year,
                'genres': ['unknown'] if not genres else list(map(lambda g: g.tag, genres)),
                'duration': self._latest_item.duration,
                'watched': self._latest_item.isWatched,
                'summary': self._latest_item.summary
                }

            if self._latest_item.type == 'episode':
                attributes['show'] = self._latest_item.show().title
                attributes['season'] = self._latest_item.seasonNumber
                attributes['episode'] = self._latest_item.index

            return attributes
