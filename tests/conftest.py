"""pytest fixtures."""
from unittest.mock import patch

import pytest

from custom_components.birthdays import Translation


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture(autouse=True)
def mock_translations():
    translation = Translation(single_day_unit='day', multiple_days_unit='days')
    with patch("custom_components.birthdays._get_translation", return_value=translation, autospec=True) as m:
        yield m
