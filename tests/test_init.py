"""Test component setup."""
from custom_components.birthdays import (
    CONF_ATTRIBUTES,
    CONF_BIRTHDAYS,
    CONF_GLOBAL_CONFIG,
    DOMAIN,
)
from homeassistant.setup import async_setup_component


async def test_async_setup__old_config_0_birthday_is_not_ok(hass):
    """Cannot have 0 birthdays configured in old config."""
    config = {DOMAIN: []}
    await _test_setup(hass, config, False)


async def test_async_setup__old_config_1_birthday_is_ok(hass):
    """1 birthday is OK in old config."""
    config = {DOMAIN: [{"name": "HomeAssistant", "date_of_birth": "2013-09-17"}]}
    await _test_setup(hass, config, True)


async def test_async_setup__new_config_0_birthday_is_not_ok(hass):
    """Cannot have 0 birthdays configured in old config."""
    config = {DOMAIN: {CONF_BIRTHDAYS: []}}
    await _test_setup(hass, config, False)


async def test_async_setup__new_config_1_birthday_is_ok(hass):
    """1 birthday is OK in new config."""
    config = {
        DOMAIN: {
            CONF_BIRTHDAYS: [{"name": "HomeAssistant", "date_of_birth": "2013-09-17"}]
        }
    }
    await _test_setup(hass, config, True)


async def test_async_setup__new_config_has_global_attributes(hass):
    """Global attributes are allowed in schema."""
    name = "HomeAssistant"
    config = {
        DOMAIN: {
            CONF_BIRTHDAYS: [{"name": name, "date_of_birth": "2013-09-17"}],
            CONF_GLOBAL_CONFIG: {CONF_ATTRIBUTES: {"message": "Hello World!"}},
        }
    }

    await _test_setup(hass, config, True)


async def _test_setup(hass, config: dict, expected_result: bool):
    assert await async_setup_component(hass, DOMAIN, config) is expected_result
