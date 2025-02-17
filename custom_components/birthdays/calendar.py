from __future__ import annotations

from datetime import date, datetime, timedelta
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DOMAIN_FRIENDLY_NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """Set up the calendar platform."""
    if discovery_info is None:
        return

    birthdays = hass.states.async_all(DOMAIN)
    birthday_events = [
        BirthdayEvent(
            birthday=datetime.strptime(b.attributes['date_of_birth'], '%Y-%m-%d').date(),
            name=b.attributes['friendly_name'],
            days_to_birthday=b.state
        ) for b in birthdays]

    if len(birthday_events) > 0:
        async_add_entities([BirthdayCalendarEntity(birthday_events)], update_before_add=True)

    return True


class BirthdayCalendarEntity(CalendarEntity):
    """Birthday calendar entity."""

    def __init__(self, events: [BirthdayEvent]) -> None:
        self._events = events
        self._attr_name = DOMAIN_FRIENDLY_NAME

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f'calendar.{DOMAIN}'

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        sorted_events: list[BirthdayEvent] = sorted(self._events, key=lambda e: e.days_to_birthday)
        for event in sorted_events:
            if not event.has_passed():
                return event.to_hass_calendar_event()

        return None

    async def async_get_events(
            self,
            hass: HomeAssistant,
            start_date: datetime,
            end_date: datetime,
    ) -> list[CalendarEvent]:
        return [event.to_hass_calendar_event()
                for event in self._events
                if self.in_range(str(event.date), start_date.date(), end_date.date())
                ]

    @staticmethod
    def in_range(isodate: str, start: date, end: date) -> bool:
        return start <= date.fromisoformat(isodate) <= end


class BirthdayEvent:
    def __init__(self, birthday: date, name: str, days_to_birthday: int):
        birth_year = birthday.year
        current_year = datetime.now().year
        self.date = birthday.replace(year=current_year)
        self.description = f'{name}, {current_year - birth_year}'
        self.days_to_birthday = days_to_birthday

    def to_hass_calendar_event(self) -> CalendarEvent:
        end = self.date + timedelta(days=1)
        return CalendarEvent(start=self.date, end=end, summary=str(self.description), description=str(self.description))

    def has_passed(self) -> bool:
        return self.date < date.today()
