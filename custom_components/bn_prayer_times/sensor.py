"""Sensors for BN Prayer Times."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, PRAYERS
from .coordinator import PrayerCoordinator
from .hijri import format_hijri

# Entities never poll; they are updated by the coordinator.
PARALLEL_UPDATES = 0


# -----------------------------------------------------
# SETUP ENTRY
# -----------------------------------------------------
async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data

    entities = []

    for prayer in PRAYERS:
        entities.append(PrayerTimeSensor(coordinator, prayer))
        entities.append(PrayerTimestampSensor(coordinator, prayer))

    entities.append(TomorrowPrayerSensor(coordinator))
    entities.append(NextPrayerSensor(coordinator))
    entities.append(HijriDateSensor(coordinator))

    # The old "Prayer Midnight Refresh" sensor was removed (the coordinator
    # already refreshes at midnight); clean up its leftover registry entry.
    registry = er.async_get(hass)
    old_id = registry.async_get_entity_id(
        "sensor", DOMAIN, "bn_prayer_midnight_refresh"
    )
    if old_id:
        registry.async_remove(old_id)

    async_add_entities(entities)


def format_12h(moment: datetime) -> str:
    return moment.strftime("%I:%M %p")


# -----------------------------------------------------
# BASE ENTITY
# -----------------------------------------------------
class BasePrayerEntity(CoordinatorEntity[PrayerCoordinator]):

    def __init__(self, coordinator: PrayerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=coordinator.district,
            manufacturer="Zam HS",
            model="Prayer Schedule",
        )


# -----------------------------------------------------
# TODAY DISPLAY SENSOR
# -----------------------------------------------------
class PrayerTimeSensor(BasePrayerEntity, SensorEntity):

    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator, prayer):
        super().__init__(coordinator)
        self.prayer = prayer
        self._attr_name = prayer
        self._attr_unique_id = f"bn_{prayer.lower()}"

    @property
    def native_value(self):
        moment = self.coordinator.data["today"].get(self.prayer)
        return format_12h(moment) if moment else None


# -----------------------------------------------------
# TIMESTAMP SENSOR
# -----------------------------------------------------
class PrayerTimestampSensor(BasePrayerEntity, SensorEntity):

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, prayer):
        super().__init__(coordinator)
        self.prayer = prayer
        self._attr_name = f"{prayer} Timestamp"
        self._attr_unique_id = f"bn_{prayer.lower()}_timestamp"

    @property
    def native_value(self):
        return self.coordinator.data["today"].get(self.prayer)


# -----------------------------------------------------
# TOMORROW SENSOR
# -----------------------------------------------------
class TomorrowPrayerSensor(BasePrayerEntity, SensorEntity):

    _attr_name = "Tomorrow Prayer"
    _attr_unique_id = "bn_tomorrow_prayer"
    _attr_icon = "mdi:calendar-clock"

    def _build(self):
        data = self.coordinator.data["tomorrow"]
        return {
            prayer.lower(): format_12h(data[prayer])
            for prayer in PRAYERS
            if prayer in data
        }

    @property
    def native_value(self):
        return " | ".join(
            f"{k.capitalize()} {v}" for k, v in self._build().items()
        )

    @property
    def extra_state_attributes(self):
        return self._build()


# -----------------------------------------------------
# NEXT PRAYER SENSOR
# -----------------------------------------------------
class NextPrayerSensor(BasePrayerEntity, SensorEntity):

    _attr_name = "Next Prayer"
    _attr_unique_id = "bn_next_prayer"
    _attr_icon = "mdi:alarm"

    # The countdown changes every second; don't store it in the database.
    _unrecorded_attributes = frozenset({"countdown"})

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._next_name = None
        self._next_time = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._recalculate()

        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._tick,
                timedelta(seconds=1),
            )
        )

    def _recalculate(self):
        now = dt_util.now()
        data = self.coordinator.data

        for prayer in PRAYERS:
            if prayer == "Imsak":
                continue

            moment = data["today"].get(prayer)
            if moment and moment > now:
                self._next_name = prayer
                self._next_time = moment
                return

        moment = data["tomorrow"].get("Subuh")
        if moment:
            self._next_name = "Subuh"
            self._next_time = moment
            return

        # No schedule left: show nothing instead of a stale prayer.
        self._next_name = None
        self._next_time = None

    @callback
    def _handle_coordinator_update(self):
        self._recalculate()
        super()._handle_coordinator_update()

    @callback
    def _tick(self, _now):
        if not self._next_time or dt_util.now() >= self._next_time:
            self._recalculate()

        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._next_name

    @property
    def extra_state_attributes(self):

        if not self._next_time:
            return None

        remaining = self._next_time - dt_util.now()
        seconds = max(0, int(remaining.total_seconds()))

        return {
            "time": format_12h(self._next_time),
            "countdown": str(timedelta(seconds=seconds)),
        }


# -----------------------------------------------------
# HIJRI SENSOR (MAGHRIB SWITCH)
# -----------------------------------------------------
class HijriDateSensor(BasePrayerEntity, SensorEntity):

    _attr_name = "Hijri Date"
    _attr_unique_id = "bn_hijri_date"
    _attr_icon = "mdi:calendar-star"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._unsub = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self._cancel_schedule)
        self._schedule()

    def _cancel_schedule(self):
        if self._unsub:
            self._unsub()
            self._unsub = None

    def _schedule(self):
        """Write the state again at the next real Maghrib time."""
        self._cancel_schedule()

        now = dt_util.now()
        data = self.coordinator.data

        maghrib = data["today"].get("Maghrib")
        if maghrib and now >= maghrib:
            maghrib = data["tomorrow"].get("Maghrib")

        if not maghrib or maghrib <= now:
            return

        self._unsub = async_track_point_in_time(
            self.hass,
            self._trigger,
            maghrib,
        )

    @callback
    def _trigger(self, _now):
        self._unsub = None
        self.async_write_ha_state()
        self._schedule()

    @callback
    def _handle_coordinator_update(self):
        self._schedule()
        super()._handle_coordinator_update()

    @property
    def native_value(self):
        now = dt_util.now()
        g_date = now.date()

        maghrib = self.coordinator.data["today"].get("Maghrib")
        if maghrib and now >= maghrib:
            g_date += timedelta(days=1)

        return format_hijri(g_date, self.coordinator.hijri_offset)
