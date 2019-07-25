import asyncio
import logging

import async_timeout
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

CONF_NAME = 'name'
CONF_DATE_OF_BIRTH = 'date_of_birth'
CONF_ICON = 'icon'
DOMAIN = 'birthdays'

BIRTHDAY_CONFIG_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_DATE_OF_BIRTH): cv.date,
    vol.Optional(CONF_ICON, default='mdi:cake'): cv.string,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [BIRTHDAY_CONFIG_SCHEMA])
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):

    devices = []

    for birthday_data in config[DOMAIN]:
        name = birthday_data[CONF_NAME]
        date_of_birth = birthday_data[CONF_DATE_OF_BIRTH]
        icon = birthday_data[CONF_ICON]
        devices.append(BirthdayEntity(name, date_of_birth, icon, hass))

    component = EntityComponent(_LOGGER, DOMAIN, hass)
    await component.async_add_entities(devices)


    tasks = [device.update_data() for device in devices]
    await asyncio.wait(tasks, loop=hass.loop)

    return True


class BirthdayEntity(Entity):

    def __init__(self, name, date_of_birth, icon, hass):
        self._name = name
        self._date_of_birth = date_of_birth
        self._icon = icon
        self._age_at_next_birthday = 0
        self._state = None
        name_in_entity_id = slugify(name)
        self.entity_id = 'birthday.{}'.format(name_in_entity_id)
        self.hass = hass

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def should_poll(self):
        # Do not poll, instead we trigger an asynchronous update every day at midnight
        return False

    @property
    def icon(self):
        return self._icon

    @property
    def device_state_attributes(self):
        return {
            CONF_DATE_OF_BIRTH: str(self._date_of_birth),
            'age_at_next_birthday': self._age_at_next_birthday,
        }

    @property
    def unit_of_measurement(self):
        return 'days'

    @property
    def hidden(self):
        return self._state is None

    def _get_seconds_until_midnight(self):
        one_day_in_seconds = 24 * 60 * 60

        now = dt_util.now()
        total_seconds_passed_today = (now.hour*60*60) + (now.minute*60) + now.second

        return one_day_in_seconds - total_seconds_passed_today

    async def update_data(self, *_):
        from datetime import date, timedelta

        today = dt_util.start_of_local_day().date()
        next_birthday = date(today.year, self._date_of_birth.month, self._date_of_birth.day)

        if next_birthday < today:
            next_birthday = next_birthday.replace(year=today.year + 1)

        days_until_next_birthday = (next_birthday-today).days

        self._age_at_next_birthday = next_birthday.year - self._date_of_birth.year
        self._state = days_until_next_birthday

        if days_until_next_birthday == 0:
            # Fire event if birthday is today
            self.hass.bus.async_fire(event_type='birthday', event_data={'name': self._name, 'age': self._age_at_next_birthday})

        await self.async_update_ha_state()
        async_call_later(self.hass, self._get_seconds_until_midnight(), self.update_data)
