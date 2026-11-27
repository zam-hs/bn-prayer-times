"""Coordinator for BN Prayer Times."""

from __future__ import annotations

import csv
import logging
from datetime import date, datetime, time, timedelta, tzinfo
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DISTRICT,
    CONF_HIJRI_OFFSET,
    DEFAULT_DISTRICT,
    DEFAULT_HIJRI_OFFSET,
    DISTRICT_TIME_OFFSET,
    DOMAIN,
    PRAYERS,
)

_LOGGER = logging.getLogger(__name__)

CSV_PATH = Path(__file__).parent / "prayers.csv"


def _load_schedule() -> dict[str, dict[str, str]]:
    """Read prayers.csv into {"YYYY-MM-DD": row}. Blocking: run in executor."""
    try:
        with CSV_PATH.open(newline="", encoding="utf-8") as file:
            return {
                row["date"]: row
                for row in csv.DictReader(file)
                if row.get("date")
            }
    except FileNotFoundError:
        _LOGGER.error("prayers.csv not found")
    except (OSError, ValueError, csv.Error) as err:
        _LOGGER.error("CSV read error: %s", err)
    return {}


class PrayerCoordinator(DataUpdateCoordinator):
    """Reads the bundled schedule once and serves today's/tomorrow's times.

    ``data`` is ``{"today": {...}, "tomorrow": {...}}`` where each inner dict
    maps a prayer name to a timezone-aware ``datetime`` with the district
    offset already applied.
    """

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(hours=6),
            always_update=False,  # only notify entities when data changes
        )

        # Options changes reload the entry, so these are fixed per instance.
        self.district: str = (
            entry.options.get(CONF_DISTRICT)
            or entry.data.get(CONF_DISTRICT)
            or DEFAULT_DISTRICT
        )

        # An offset of 0 is valid, so check for None, not falsiness.
        offset = entry.options.get(CONF_HIJRI_OFFSET)
        if offset is None:
            offset = entry.data.get(CONF_HIJRI_OFFSET, DEFAULT_HIJRI_OFFSET)
        self.hijri_offset: int = int(offset)

        self._district_minutes = DISTRICT_TIME_OFFSET.get(self.district, 0)
        self._schedule: dict[str, dict[str, str]] | None = None
        self._unsub_midnight = None
        self._warned_for: date | None = None

    async def async_config_entry_first_refresh(self) -> None:
        """Initial refresh, then refresh every local midnight."""
        await super().async_config_entry_first_refresh()
        self._unsub_midnight = async_track_time_change(
            self.hass, self._handle_midnight, hour=0, minute=0, second=0
        )

    async def async_shutdown(self) -> None:
        """Cancel the midnight timer when the config entry is unloaded."""
        if self._unsub_midnight:
            self._unsub_midnight()
            self._unsub_midnight = None
        await super().async_shutdown()

    async def _handle_midnight(self, _now: datetime) -> None:
        _LOGGER.debug("BN Prayer Times midnight refresh")
        # Refresh directly (not debounced) so the new day is ready at once.
        await self.async_refresh()

    async def _async_update_data(self) -> dict[str, dict[str, datetime]]:
        if self._schedule is None:
            # The file is read once; later refreshes only do dict lookups.
            self._schedule = await self.hass.async_add_executor_job(
                _load_schedule
            )

        # Use the Home Assistant timezone, not the system clock's.
        now = dt_util.now()
        today = now.date()

        data = {
            "today": self._times_for(today, now.tzinfo),
            "tomorrow": self._times_for(today + timedelta(days=1), now.tzinfo),
        }

        if not data["today"] and self._warned_for != today:
            self._warned_for = today
            _LOGGER.warning(
                "No prayer times for %s in prayers.csv; "
                "update the integration to get the newest schedule",
                today,
            )

        return data

    def _times_for(self, day: date, tz: tzinfo | None) -> dict[str, datetime]:
        """Return {prayer: aware datetime} for a day, district offset applied."""
        row = self._schedule.get(day.isoformat()) if self._schedule else None
        if not row:
            return {}

        times: dict[str, datetime] = {}
        for prayer in PRAYERS:
            value = row.get(prayer)
            if not value:
                continue
            try:
                hour, minute = value.split(":")
                moment = datetime.combine(
                    day, time(int(hour), int(minute)), tzinfo=tz
                )
            except ValueError:
                _LOGGER.warning(
                    "Invalid %s time %r on %s in prayers.csv",
                    prayer,
                    value,
                    day,
                )
                continue
            times[prayer] = moment + timedelta(minutes=self._district_minutes)

        return times
