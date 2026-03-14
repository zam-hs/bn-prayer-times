DOMAIN = "bn_prayer_times"

PRAYERS = [
    "Imsak",
    "Subuh",
    "Syuruk",
    "Zohor",
    "Asar",
    "Maghrib",
    "Isyak",
]

CONF_HIJRI_OFFSET = "hijri_offset"
DEFAULT_HIJRI_OFFSET = 0

# ✅ District support
CONF_DISTRICT = "district"
DEFAULT_DISTRICT = "Brunei/Muara"

DISTRICT_OPTIONS = [
    "Brunei/Muara",
    "Temburong",
    "Tutong",
    "Kuala Belait",
]

DISTRICT_TIME_OFFSET = {
    "Brunei/Muara": 0,
    "Temburong": 0,
    "Tutong": 1,
    "Kuala Belait": 3,
}
