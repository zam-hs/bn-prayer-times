from __future__ import annotations

import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class PrayerCoordinator(DataUpdateCoordinator):
    """Coordinator to manage prayer time data."""

    def __init__(self, hass: HomeAssistant, entry):
        """Initialize coordinator."""
        self.hass = hass
        self.entry = entry
        self._unsub_midnight = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=6),
        )

    async def async_config_entry_first_refresh(self):
        """Initial refresh and schedule midnight update."""
        await super().async_config_entry_first_refresh()
        self._schedule_midnight_refresh()

    # -------------------------------------------------
    # Midnight refresh
    # -------------------------------------------------
    def _schedule_midnight_refresh(self):
        """Schedule refresh exactly at midnight."""

        now = dt_util.now()

        midnight = datetime.combine(
            now.date() + timedelta(days=1),
            datetime.min.time(),
        )

        midnight = dt_util.as_local(
            dt_util.as_utc(
                midnight.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            )
        )

        if self._unsub_midnight:
            self._unsub_midnight()

        self._unsub_midnight = async_track_point_in_time(
            self.hass,
            self._handle_midnight,
            midnight,
        )

    async def _handle_midnight(self, *_):
        """Handle midnight refresh."""
        _LOGGER.debug("BN Prayer Times midnight refresh")

        await self.async_request_refresh()

        # reschedule next midnight
        self._schedule_midnight_refresh()

    # -------------------------------------------------
    # CSV loader
    # -------------------------------------------------
    def _read_csv(self):
        """Read prayer CSV."""

        csv_path = Path(__file__).parent / "prayers.csv"

        if not csv_path.exists():
            _LOGGER.error("prayers.csv not found")
            return {}

        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (
            datetime.now() + timedelta(days=1)
        ).strftime("%Y-%m-%d")

        today_row = {}
        tomorrow_row = {}

        try:
            with open(csv_path, newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                for row in reader:
                    if row.get("date") == today:
                        today_row = row

                    elif row.get("date") == tomorrow:
                        tomorrow_row = row

        except Exception as err:
            _LOGGER.error("CSV read error: %s", err)

        return {
            "today": today_row,
            "tomorrow": tomorrow_row,
        }

    async def _async_update_data(self):
        """Update prayer data."""
        return await self.hass.async_add_executor_job(
            self._read_csv
        )
