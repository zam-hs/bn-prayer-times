from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.event import (
    async_track_time_interval,
    async_track_point_in_time,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    PRAYERS,
    DISTRICT_TIME_OFFSET,
    CONF_DISTRICT,
    CONF_HIJRI_OFFSET,
)


# -----------------------------------------------------
# SETUP ENTRY
# -----------------------------------------------------
async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    for prayer in PRAYERS:
        entities.append(PrayerTimeSensor(coordinator, prayer))
        entities.append(PrayerTimestampSensor(coordinator, prayer))

    entities.append(TomorrowPrayerSensor(coordinator))
    entities.append(NextPrayerSensor(coordinator))
    entities.append(HijriDateSensor(coordinator))
    entities.append(MidnightRefreshSensor(coordinator))  # ⭐ new

    async_add_entities(entities)


# -----------------------------------------------------
# HIJRI SUPPORT
# -----------------------------------------------------
HIJRI_MONTHS = [
    "Muharram","Safar","Rabi' al-Awwal","Rabi' al-Thani",
    "Jumada al-Ula","Jumada al-Thani","Rajab","Sha'ban",
    "Ramadan","Shawwal","Dhu al-Qi'dah","Dhu al-Hijjah",
]


def gregorian_to_hijri(g_date):
    jd = g_date.toordinal() + 1721424
    l = jd - 1948440 + 10632
    n = (l - 1) // 10631
    l = l - 10631 * n + 354
    j = (
        ((10985 - l) // 5316) * ((50 * l) // 17719)
        + (l // 5670) * ((43 * l) // 15238)
    )
    l = (
        l
        - ((30 - j) // 15) * ((17719 * j) // 50)
        - (j // 16) * ((15238 * j) // 43)
        + 29
    )
    month = (24 * l) // 709
    day = l - (709 * month) // 24
    year = 30 * n + j - 30
    return int(day), int(month), int(year)


# -----------------------------------------------------
# UTILITIES
# -----------------------------------------------------
def get_district(entry):
    return (
        entry.options.get(CONF_DISTRICT)
        or entry.data.get(CONF_DISTRICT)
        or "Brunei/Muara"
    )


def apply_district_offset(coordinator, timestr):
    if not timestr:
        return None

    district = get_district(coordinator.entry)
    offset = DISTRICT_TIME_OFFSET.get(district, 0)

    dt = datetime.strptime(timestr, "%H:%M")
    dt += timedelta(minutes=offset)
    return dt


def format_12h(dt):
    return dt.strftime("%I:%M %p")


def build_local_datetime(time_obj, days_add=0):
    base = dt_util.now().date() + timedelta(days=days_add)
    naive = datetime.combine(base, time_obj)

    return dt_util.as_local(
        dt_util.as_utc(
            naive.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        )
    )


# -----------------------------------------------------
# BASE ENTITY
# -----------------------------------------------------
class BasePrayerEntity(CoordinatorEntity):

    def __init__(self, coordinator):
        super().__init__(coordinator)

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=get_district(self.coordinator.entry),
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
        data = self.coordinator.data.get("today", {})
        dt = apply_district_offset(self.coordinator, data.get(self.prayer))
        return format_12h(dt) if dt else None


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
        data = self.coordinator.data.get("today", {})
        dt = apply_district_offset(self.coordinator, data.get(self.prayer))
        return build_local_datetime(dt.time()) if dt else None


# -----------------------------------------------------
# TOMORROW SENSOR
# -----------------------------------------------------
class TomorrowPrayerSensor(BasePrayerEntity, SensorEntity):

    _attr_name = "Tomorrow Prayer"
    _attr_unique_id = "bn_tomorrow_prayer"
    _attr_icon = "mdi:calendar-clock"

    def _build(self):
        data = self.coordinator.data.get("tomorrow", {})
        out = {}

        for prayer in PRAYERS:
            dt = apply_district_offset(self.coordinator, data.get(prayer))
            if dt:
                out[prayer.lower()] = format_12h(dt)

        return out

    @property
    def native_value(self):
        res = self._build()
        return " | ".join(f"{k.capitalize()} {v}" for k, v in res.items())

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

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._next_name = None
        self._next_time = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._recalculate()

        async_track_time_interval(
            self.hass,
            self._tick,
            timedelta(seconds=1),
        )

    def _recalculate(self):
        now = dt_util.now()
        today = self.coordinator.data.get("today", {})

        for prayer in PRAYERS:
            if prayer == "Imsak":
                continue

            dt = apply_district_offset(self.coordinator, today.get(prayer))
            if not dt:
                continue

            prayer_dt = build_local_datetime(dt.time())

            if prayer_dt > now:
                self._next_name = prayer
                self._next_time = prayer_dt
                return

        tomorrow = self.coordinator.data.get("tomorrow", {})
        dt = apply_district_offset(self.coordinator, tomorrow.get("Subuh"))

        if dt:
            self._next_name = "Subuh"
            self._next_time = build_local_datetime(dt.time(), days_add=1)

    async def _tick(self, *_):
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
        self._schedule()

    def _schedule(self):
        today = self.coordinator.data.get("today", {})
        maghrib = today.get("Maghrib")

        if not maghrib:
            return

        dt = apply_district_offset(self.coordinator, maghrib)
        maghrib_dt = build_local_datetime(dt.time())

        if dt_util.now() >= maghrib_dt:
            maghrib_dt += timedelta(days=1)

        if self._unsub:
            self._unsub()

        self._unsub = async_track_point_in_time(
            self.hass,
            self._trigger,
            maghrib_dt,
        )

    async def _trigger(self, *_):
        self.async_write_ha_state()
        self._schedule()

    @property
    def native_value(self):

        now = dt_util.now()
        today = self.coordinator.data.get("today", {})
        maghrib = today.get("Maghrib")

        g_date = now.date()

        if maghrib:
            dt = apply_district_offset(self.coordinator, maghrib)
            maghrib_dt = build_local_datetime(dt.time())

            if now >= maghrib_dt:
                g_date += timedelta(days=1)

        h_day, h_month, h_year = gregorian_to_hijri(
            datetime.combine(g_date, datetime.min.time())
        )

        offset = int(
            self.coordinator.entry.options.get(CONF_HIJRI_OFFSET)
            or self.coordinator.entry.data.get(CONF_HIJRI_OFFSET, 0)
        )

        h_day += offset

        return f"{h_day} {HIJRI_MONTHS[h_month-1]} {h_year} AH"


# -----------------------------------------------------
# MIDNIGHT REFRESH TRIGGER
# -----------------------------------------------------
class MidnightRefreshSensor(BasePrayerEntity, SensorEntity):

    _attr_name = "Prayer Midnight Refresh"
    _attr_unique_id = "bn_prayer_midnight_refresh"
    _attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._schedule()

    def _schedule(self):

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

        async_track_point_in_time(
            self.hass,
            self._trigger,
            midnight,
        )

    async def _trigger(self, *_):
        await self.coordinator.async_request_refresh()
        self._schedule()

    @property
    def native_value(self):
        return "scheduled"
