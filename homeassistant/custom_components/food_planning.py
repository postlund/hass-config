"""Fetch food planning from google doc and present as sensors."""
import re
import os
import asyncio
import logging
import datetime
from datetime import timedelta

import voluptuous as vol

from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import (
    async_dispatcher_send, async_dispatcher_connect)
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util.dt import utcnow
from homeassistant.core import callback
from homeassistant.components import group

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'food_planning'

REQUIREMENTS = ['PyDrive==1.3.1']

DEPENDENCIES = ['group']

CONF_DAYS = 'days'
CONF_DAY_NAME = 'day_name'
CONF_DAY_NUMBER = 'day_number'
CONF_FILE_ID = 'file_id'
CONF_GROUP = 'group'

ATTR_TODAY = 'today'
ATTR_LINK = 'link'
ATTR_CUSTOM_UI = 'custom_ui_state_card'

DATA_FOOD_PLANNING = 'data_food_planning'
SIGNAL_FOOD_DATA_UPDATED = 'food_data_updated'

SCAN_INTERVAL = timedelta(seconds=3600)

CONFIG_FILE = 'food_planning.yaml'
TEMP_FILE_BASE = '/tmp/pydrive_tmp_'

URL_REGEX = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+' # noqa

ENTITIES_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_DAY_NUMBER): vol.Range(min=0, max=6),
    vol.Required(CONF_DAY_NAME): cv.string,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_FILE_ID): cv.string,
        vol.Required(CONF_DAYS): [ENTITIES_SCHEMA],
        vol.Optional(CONF_GROUP, default='Food Menu'): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.CRITICAL)
logging.getLogger('googleapiclient.discovery').setLevel(logging.CRITICAL)


def _fetch_file(settings_file, file_id, outfile):
    from pydrive.auth import GoogleAuth
    from pydrive.drive import GoogleDrive

    gauth = GoogleAuth(settings_file=settings_file)
    drive = GoogleDrive(gauth)

    file = drive.CreateFile({'id': file_id})
    file.FetchMetadata()
    file.GetContentFile(outfile, mimetype='text/plain')


def _read_file(outfile):
    data = ''
    cnt = 0

    with open(outfile, 'r', encoding='utf-8') as file_handle:
        for line in file_handle:
            if len(line) == 1:
                cnt += 1
            else:
                cnt = 0
                data += line

            if cnt == 4:
                break

    return data


def parse_food_menu(raw_menu, day_list):
    """Parse a food menu and return as a dict."""
    day_regex = r'\s*({0})\s*'.format('|'.join(day_list))
    result = {}
    started = False
    current_day = None

    for line in (raw_menu.rstrip() + '\n' + day_list[0]).split('\n'):
        if re.match(day_regex, line):
            started = True
            current_day = line.lstrip()
        elif started:
            fixed = line.rstrip().lstrip()
            if current_day in result:
                result[current_day] += ', ' + fixed
            else:
                result[current_day] = fixed
            result[current_day] = result[current_day][0:254]

    return result


@asyncio.coroutine
def async_setup(hass, config):
    """Set up the food planning component."""
    domain = config.get(DOMAIN)
    file_id = domain.get(CONF_FILE_ID)
    days = domain.get(CONF_DAYS)
    settings_file = hass.config.path(CONFIG_FILE)

    hass.data[DATA_FOOD_PLANNING] = {}

    day_names = [x.get(CONF_DAY_NAME) for x in days]

    @asyncio.coroutine
    def get_week_food_planning(file_id):
        """Extract and save food planning."""
        outfile = TEMP_FILE_BASE + file_id

        try:
            yield from hass.loop.run_in_executor(
                None, _fetch_file, settings_file, file_id, outfile)
            data = yield from hass.loop.run_in_executor(
                None, _read_file, outfile)

            return parse_food_menu(data, day_names)

        finally:
            os.unlink(outfile)

        return {}

    @asyncio.coroutine
    def async_update_data(now):  # pylint: disable=unused-argument
        """Update data from google drive."""
        try:
            hass.data[DATA_FOOD_PLANNING] = yield from get_week_food_planning(
                file_id)
            async_dispatcher_send(hass, SIGNAL_FOOD_DATA_UPDATED)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception('failed to update')

        async_track_point_in_utc_time(
            hass, async_update_data, utcnow() + SCAN_INTERVAL)

    ents = []
    for link in domain.get(CONF_DAYS):
        sensor = DayFoodSensor(
            hass, link.get(CONF_NAME),
            link.get(CONF_DAY_NAME), link.get(CONF_DAY_NUMBER))
        ents.append(sensor.entity_id)

    yield from async_update_data(None)

    data = {
        group.ATTR_OBJECT_ID: 'food_planning_group',
        group.ATTR_NAME: domain.get(CONF_GROUP),
        group.ATTR_ENTITIES: ents,
    }

    yield from hass.services.async_call(
        group.DOMAIN, group.SERVICE_SET, data)

    return True


class DayFoodSensor(Entity):
    """Representation of a food sensor."""

    def __init__(self, hass, name, day_name, day_number):
        """Initialize the link."""
        self.hass = hass
        self._name = name
        self._value = None
        self._day_name = day_name
        self._day_number = day_number
        self._link = ""
        self.entity_id = DOMAIN + '.%s' % slugify(name)
        self.subscribe()

    def subscribe(self):
        """Register update dispatcher."""
        @callback
        def async_update():
            """Update callback."""
            data = self.hass.data[DATA_FOOD_PLANNING]
            planned_for_day = data.get(self._day_name, None)
            if planned_for_day != self._value:
                self._value, self._link = self._extract_link(planned_for_day)
                self.hass.async_add_job(self.async_update_ha_state(True))

        async_dispatcher_connect(
            self.hass, SIGNAL_FOOD_DATA_UPDATED, async_update)

    @staticmethod
    def _extract_link(planned_for_day):
        value = planned_for_day or 'Nothing planned'
        link = ''

        urls = re.findall(URL_REGEX, value)
        if len(urls) > 0:
            link = urls[0]
            for link in urls:
                value = value.replace(link, '')

        return value, link

    @property
    def name(self):
        """Return the name of the URL."""
        return self._name

    @property
    def state(self):
        """Return the state."""
        return self._value

    @property
    def should_poll(self):
        """Polling is not needed."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        weekday_number = datetime.datetime.now().weekday()
        params = {
            ATTR_CUSTOM_UI: 'state-card-food-planning',
            ATTR_LINK: self._link,
            ATTR_TODAY: (self._day_number == weekday_number),
            }
        return params
