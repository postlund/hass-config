"""Support for system log collector."""
import logging
from collections import deque

import voluptuous as vol

from homeassistant.helpers.entity import Entity


DOMAIN = 'system_log_collector'

SERVICE_CLEAR_SCHEMA = vol.Schema({})

_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument
async def async_setup_platform(hass, config, async_add_devices,
                               discovery_info=None):
    """Set up the system logger collector component."""

    sensor = SystemLogCollectorSensor(hass)

    async def async_service_handler(service):
        """Handle logger services."""
        if service.data['domain'] == 'system_log' and service.data['service'] == 'clear':
            sensor.actions.clear()
            sensor.async_schedule_update_ha_state()

    async def async_log_event(event):
        """Handle new system log event."""
        msg = event.data.get('message', '')
        if 'frontend_latest/' in msg:
            return

        src = event.data['source']
        exists = [x for x in sensor.actions if
                  x['message'] == msg and x['source'] == src]
        if not any(exists):
            sensor.actions.appendleft(event.data)
            sensor.async_schedule_update_ha_state()

    async_add_devices([sensor])

    hass.bus.async_listen('call_service', async_service_handler)
    hass.bus.async_listen('system_log_event', async_log_event)

    return True


class SystemLogCollectorSensor(Entity):
    """Implementation of a system log collector sensor."""

    def __init__(self, hass):
        """Initialize the sensor."""
        self.hass = hass
        self.actions = deque(maxlen=50)

    @property
    def name(self):
        """Return name of sensor."""
        return 'log_collector'

    @property
    def state(self):
        """Return state of sensor."""
        if self.actions:
            return self.actions[0]['message']
        return 'none'

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def state_attributes(self):
        """Return the state attributes."""
        cnt = len(self.actions)
        state_attr = {
            'actions': list(self.actions),
            'no_events': len(self.actions),
            'first': (None if cnt < 1 else self.actions[0]),
            'second': (None if cnt < 2 else self.actions[1]),
            'third': (None if cnt < 3 else self.actions[2]),
            'fourth': (None if cnt < 4 else self.actions[3]),
            'fifth': (None if cnt < 5 else self.actions[4]),
        }
        return state_attr
