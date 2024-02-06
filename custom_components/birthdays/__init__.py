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

CONF_UNIQUE_ID = 'unique_id'
CONF_NAME = 'name'
CONF_DATE_OF_BIRTH = 'date_of_birth'
CONF_ICON = 'icon'
CONF_ATTRIBUTES = 'attributes'
CONF_AGE_AT_NEXT_BIRTHDAY = 'age_at_next_birthday'
DOMAIN = 'birthdays'

BIRTHDAY_CONFIG_SCHEMA = vol.Schema({
    vol.Optional(CONF_UNIQUE_ID, default=None): cv.string,
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_DATE_OF_BIRTH): cv.date,
    vol.Optional(CONF_ICON, default='mdi:cake'): cv.string,
    vol.Optional(CONF_ATTRIBUTES, default={}): vol.Schema({cv.string: cv.string}),
    vol.Optional(CONF_AGE_AT_NEXT_BIRTHDAY, default=1): cv.positive_int,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [BIRTHDAY_CONFIG_SCHEMA])
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):

    devices = []

    for birthday_data in config[DOMAIN]:
        unique_id            = birthday_data[CONF_UNIQUE_ID]
        name                 = birthday_data[CONF_NAME]
        date_of_birth        = birthday_data[CONF_DATE_OF_BIRTH]
        icon                 = birthday_data[CONF_ICON]
        attributes           = birthday_data[CONF_ATTRIBUTES]
        age_at_next_birthday = birthday_data[CONF_AGE_AT_NEXT_BIRTHDAY]
        devices.append(BirthdayEntity(unique_id, name, date_of_birth, icon, attributes, age_at_next_birthday, hass))

    component = EntityComponent(_LOGGER, DOMAIN, hass)
    await component.async_add_entities(devices)


    tasks = [asyncio.create_task(device.update_data()) for device in devices]
    await asyncio.wait(tasks)

    _LOGGER.debug(devices)

    return True


class BirthdayEntity(Entity):

    def __init__(self, unique_id, name, date_of_birth, icon, attributes, age_at_next_birthday, hass):
        self._name = name

        if unique_id is not None:
            self._unique_id = slugify(unique_id)
        else: 
            self._unique_id = slugify(name)

        self._state                = None
        self._icon                 = icon
        self._date_of_birth        = date_of_birth
        self._age_at_next_birthday = age_at_next_birthday
        self._entity_id            = '{}.{}'.format(DOMAIN, self._unique_id)
        self.hass                  = hass

        self._extra_state_attributes = {
            CONF_DATE_OF_BIRTH: str(self._date_of_birth),
            CONF_AGE_AT_NEXT_BIRTHDAY: self._age_at_next_birthday,
        }

        if len(attributes) > 0 and attributes is not None:
            for k,v in attributes.items():
                self._extra_state_attributes[k] = v

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return '{}.{}'.format(self._entity_id, slugify(self._date_of_birth.strftime("%Y%m%d")))

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
    def extra_state_attributes(self):
        return self._extra_state_attributes

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

        age = next_birthday.year - self._date_of_birth.year
        self._age_at_next_birthday = age
        self._extra_state_attributes[CONF_AGE_AT_NEXT_BIRTHDAY] = age

        
        self._state = days_until_next_birthday

        if days_until_next_birthday == 0:
            # Fire event if birthday is today
            self.hass.bus.async_fire(event_type='birthday', event_data={'name': self._name, 'age': age})

        self.async_write_ha_state()
        async_call_later(self.hass, self._get_seconds_until_midnight(), self.update_data)
