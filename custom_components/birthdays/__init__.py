import asyncio
from dataclasses import dataclass
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (Platform)
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.template import Template, is_template_string, render_complex
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util, slugify

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_UNIQUE_ID = 'unique_id'
CONF_NAME = 'name'
CONF_DATE_OF_BIRTH = 'date_of_birth'
CONF_ICON = 'icon'
CONF_ATTRIBUTES = 'attributes'
CONF_GLOBAL_CONFIG = 'config'
CONF_BIRTHDAYS = 'birthdays'
CONF_AGE_AT_NEXT_BIRTHDAY = 'age_at_next_birthday'

BIRTHDAY_CONFIG_SCHEMA = vol.Schema({
    vol.Optional(CONF_UNIQUE_ID): cv.string,
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_DATE_OF_BIRTH): cv.date,
    vol.Optional(CONF_ICON, default='mdi:cake'): cv.string,
    vol.Optional(CONF_ATTRIBUTES, default={}): vol.Schema({cv.string: cv.string}),
})

GLOBAL_CONFIG_SCHEMA = vol.Schema({
    vol.Optional(CONF_ATTRIBUTES, default={}): vol.Schema({cv.string: cv.string}),
})

# Old schema (list of birthday configurations)
OLD_CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [BIRTHDAY_CONFIG_SCHEMA])
}, extra=vol.ALLOW_EXTRA)

# New schema (supports both global and birthday configs)
NEW_CONFIG_SCHEMA = vol.Schema({
    DOMAIN: {
        CONF_BIRTHDAYS: vol.All(cv.ensure_list, [BIRTHDAY_CONFIG_SCHEMA]),
        vol.Optional(CONF_GLOBAL_CONFIG, default={}): GLOBAL_CONFIG_SCHEMA
    }
}, extra=vol.ALLOW_EXTRA)

# Use vol.Any() to support both old and new schemas
CONFIG_SCHEMA = vol.Schema(vol.Any(
    OLD_CONFIG_SCHEMA,
    NEW_CONFIG_SCHEMA
), extra=vol.ALLOW_EXTRA)


@dataclass
class Translation:
    single_day_unit: str
    multiple_days_unit: str


async def async_setup(hass, config):
    devices = []

    is_new_config = isinstance(config[DOMAIN], dict) and config[DOMAIN].get(CONF_BIRTHDAYS) is not None
    birthdays = config[DOMAIN][CONF_BIRTHDAYS] if is_new_config else config[DOMAIN]
    translation = await _get_translation(hass)

    for birthday_data in birthdays:
        unique_id = birthday_data.get(CONF_UNIQUE_ID)
        name = birthday_data[CONF_NAME]
        date_of_birth = birthday_data[CONF_DATE_OF_BIRTH]
        icon = birthday_data[CONF_ICON]
        attributes = birthday_data[CONF_ATTRIBUTES]
        if is_new_config:
            global_config = config[DOMAIN][CONF_GLOBAL_CONFIG]  # Empty dict or has attributes
            global_attributes = global_config.get(CONF_ATTRIBUTES) or {}
            attributes = dict(global_attributes,
                              **attributes)  # Add global_attributes but let local attributes be on top

        devices.append(BirthdayEntity(unique_id, name, date_of_birth, icon, attributes, translation, hass))

    # Set up component
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    await component.async_add_entities(devices)

    # Update state
    tasks = [asyncio.create_task(device.update_data()) for device in devices]
    await asyncio.wait(tasks)

    _LOGGER.debug(devices)
    hass.async_create_task(async_load_platform(hass, Platform.CALENDAR, DOMAIN, {}, config))

    return True


async def _get_translation(hass) -> Translation:
    """Fetch the translated units of measurement and update each sensor."""
    category = "config"
    translations = await async_get_translations(hass,
                                                language=hass.config.language,
                                                category=category,
                                                integrations=[DOMAIN])

    base_key = f'component.{DOMAIN}.{category}.unit_of_measurement'

    single_day_unit = translations.get(f'{base_key}.single_day', 'day')
    multiple_days_unit = translations.get(f'{base_key}.multiple_days', 'days')

    return Translation(single_day_unit=single_day_unit, multiple_days_unit=multiple_days_unit)


class BirthdayEntity(Entity):

    def __init__(self, unique_id, name, date_of_birth, icon, attributes, translation, hass):
        self._name = name

        if unique_id is not None:
            self._unique_id = slugify(unique_id)
        else:
            self._unique_id = slugify(name)

        self._state = None
        self._icon = icon
        self._date_of_birth = date_of_birth
        self.hass = hass

        self._extra_state_attributes = {
            CONF_DATE_OF_BIRTH: str(self._date_of_birth),
        }
        self._templated_attributes = {}

        if len(attributes) > 0 and attributes is not None:
            for k, v in attributes.items():
                if is_template_string(v):
                    _LOGGER.info(f'{v} is a template and will be evaluated at runtime')
                    self._templated_attributes[k] = Template(template=v, hass=hass)
                else:
                    self._extra_state_attributes[k] = v

        self._translation: Translation = translation

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

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
        for key, templated_value in self._templated_attributes.items():
            value = render_complex(templated_value, variables={"this": self})
            self._extra_state_attributes[key] = value

        return self._extra_state_attributes

    @property
    def date_of_birth(self):
        return self._date_of_birth

    @property
    def unit_of_measurement(self):
        return self._translation.single_day_unit \
            if self._state is not None and self._state == 1 \
            else self._translation.multiple_days_unit

    @property
    def hidden(self):
        return self._state is None

    @staticmethod
    def _get_seconds_until_midnight():
        one_day_in_seconds = 24 * 60 * 60

        now = dt_util.now()
        total_seconds_passed_today = (now.hour * 60 * 60) + (now.minute * 60) + now.second

        return one_day_in_seconds - total_seconds_passed_today

    async def update_data(self, *_):
        from datetime import date

        today = dt_util.start_of_local_day().date()
        next_birthday = date(today.year, self._date_of_birth.month, self._date_of_birth.day)

        if next_birthday < today:
            next_birthday = next_birthday.replace(year=today.year + 1)

        days_until_next_birthday = (next_birthday - today).days

        age = next_birthday.year - self._date_of_birth.year
        self._extra_state_attributes[CONF_AGE_AT_NEXT_BIRTHDAY] = age

        self._state = days_until_next_birthday

        if days_until_next_birthday == 0:
            # Fire event if birthday is today
            self.hass.bus.async_fire(event_type='birthday', event_data={'name': self._name, 'age': age})

        self.async_write_ha_state()
        async_call_later(self.hass, self._get_seconds_until_midnight(), self.update_data)
