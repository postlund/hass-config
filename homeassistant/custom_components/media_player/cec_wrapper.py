"""Simple CEC wrapper to control my old TV.

This is a quick hack with lots of bad stuff...
"""

import time
import logging
from functools import partial

import cec

_LOGGER = logging.getLogger(__name__)


class CecWrapper:
    """Control TV device via CEC."""

    def __init__(self):
        """Initialize a new CecWrapper instance."""
        self.cecconfig = cec.libcec_configuration()
        self.cecconfig.strDeviceName = "pyLibCec"
        self.cecconfig.bActivateSource = 0
        self.cecconfig.deviceTypes.Add(cec.CEC_DEVICE_TYPE_RECORDING_DEVICE)
        self.cecconfig.clientVersion = cec.LIBCEC_VERSION_CURRENT
        self.cecconfig.SetLogCallback(partial(self._log_callback))

        self.lib = cec.ICECAdapter.Create(self.cecconfig)
        self.callback = None
        self._is_on = None

    def open(self):
        """Open connection to the CEC device."""
        adapters = self.lib.DetectAdapters()
        if not adapters:
            raise Exception('no CEC adapter found')

        if not self.lib.Open(adapters[0].strComName):
            raise Exception('failed to open CEC adapter')

    def _tx(self, cmd):
        self.lib.Transmit(self.lib.CommandFromString(cmd))

    def turn_on(self):
        """Turn on TV."""
        self._tx('80:44:40')

    def turn_off(self):
        """Turn off TV."""
        self._tx('80:36')

    def change_source(self):
        """Change input to HDMI1."""
        self._tx('8F:82:10:00')

    def _change_state(self, to_state):
        if self._is_on is None or self._is_on != to_state:
            self._is_on = to_state
            try:
                if self.callback is not None:
                    self.callback(self._is_on)
            except:  # noqa  # pylint: disable=bare-except
                _LOGGER.exception('Failed to update state')

    def _handle_traffic(self, message):
        incoming = message.split(' ')[0] == '>>'
        data = message.split(' ')[1].split(':')

        if len(data) < 2:
            return

        if data[1] == '36':
            self._change_state(False)
        elif incoming:
            if data[1] == '90':
                self._change_state(data[2] == '00')
            elif data[1:] == ['89', '10', '01', '02']:
                self._tx('80:8F')  # Get status from device

    def _log_callback(self, level, timestamp, message):
        if level == cec.CEC_LOG_ERROR:
            levelstr = "ERROR:   "
        elif level == cec.CEC_LOG_WARNING:
            levelstr = "WARNING: "
        elif level == cec.CEC_LOG_NOTICE:
            levelstr = "NOTICE:  "
        elif level == cec.CEC_LOG_TRAFFIC:
            levelstr = "TRAFFIC: "
            try:
                self._handle_traffic(message)
            except:  # noqa  # pylint: disable=bare-except
                _LOGGER.exception('Error while parsing traffic')
        elif level == cec.CEC_LOG_DEBUG:
            levelstr = "DEBUG:   "

        _LOGGER.info('%s [%s] %s', levelstr, timestamp, message)
        return 0


def main():
    """Simple test of class above."""
    def callback(is_on):
        print('=> TV is', 'ON' if is_on else 'OFF')

    wrapper = CecWrapper()
    wrapper.callback = callback
    wrapper.open()
    wrapper.turn_on()
    time.sleep(10)
    wrapper.change_source()
    time.sleep(20)
    wrapper.turn_off()


if __name__ == '__main__':
    main()
