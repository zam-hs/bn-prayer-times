"""Hijri date helpers (pure Python, no Home Assistant imports)."""

from __future__ import annotations

from datetime import date, timedelta

HIJRI_MONTHS = (
    "Muharram",
    "Safar",
    "Rabiulawal",
    "Rabiulakhir",
    "Jamadilawal",
    "Jamadilakhir",
    "Rejab",
    "Sya'ban",
    "Ramadhan",
    "Syawal",
    "Zulkaedah",
    "Zulhijjah",
)


def gregorian_to_hijri(g_date: date) -> tuple[int, int, int]:
    """Convert a Gregorian date to a (day, month, year) Hijri tuple."""
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


def format_hijri(g_date: date, offset: int = 0) -> str:
    """Return e.g. '12 Rejab 1448 AH'.

    The Gregorian date is shifted by the offset *before* converting, so the
    month rolls over by itself (never '0 Muharram' or '31 Safar').
    """
    h_day, h_month, h_year = gregorian_to_hijri(g_date + timedelta(days=offset))
    return f"{h_day} {HIJRI_MONTHS[h_month - 1]} {h_year} AH"
