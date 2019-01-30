"""Hack-ish component to turn on/off and get status for my old TV.

My old Panasonc TH-50PZ70E has very poor CEC support, so the regular hdmi_cec
is not usable. This component implements gooe enough support for the following:

  * Turn on
  * Turn off
  * Get status (if on or off)
  * Change to input to HDMI1

No support is given.
"""
import logging

from homeassistant.components import hdmi_cec
from homeassistant.components.media_player import (
    MediaPlayerDevice, SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF, SUPPORT_TURN_ON)
from homeassistant.const import (STATE_PLAYING, STATE_OFF)
from homeassistant.exceptions import PlatformNotReady

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = hdmi_cec.REQUIREMENTS


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the CEC TV platform."""
    from .cec_wrapper import CecWrapper

    try:
        wrapper = CecWrapper()
        device = TvCecDevice(wrapper)
        add_entities([device])
        hass.add_job(wrapper.open)
    except:  # noqa
        _LOGGER.error('Failed to open CEC device')
        raise PlatformNotReady


class TvCecDevice(MediaPlayerDevice):
    """Representation of a CEC TV."""

    def __init__(self, wrapper):
        """Initialize the device."""
        self.wrapper = wrapper
        self.wrapper.callback = self._is_on_callback
        self._state = STATE_OFF

    def _is_on_callback(self, is_on):
        self._state = STATE_PLAYING if is_on else STATE_OFF
        _LOGGER.info('Updating state to %d', self._state)
        self.schedule_update_ha_state()

    @property
    def name(self):
        """Return the device name."""
        return 'TV'

    @property
    def should_poll(self):
        """Device should be polled."""
        return False

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_SELECT_SOURCE

    @property
    def state(self):
        """Return the state of the player."""
        return self._state

    @property
    def source_list(self):
        """Return a list of running apps."""
        return ['HDMI1']

    def turn_on(self):
        """Turn on the device."""
        self.wrapper.turn_on()

    def turn_off(self):
        """Turn off the device."""
        self.wrapper.turn_off()

    def select_source(self, source):
        """Select input source."""
        if source == 'HDMI1':
            self.wrapper.change_source()
