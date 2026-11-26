## 1.0.0
- Initial release

## 1.0.1
- Update hijri months

## 1.0.2
- Add logo and dark variants; use visible green icon for light theme

## 1.0.3
- Use the Home Assistant timezone (`dt_util.now()`) when looking up today and tomorrow
- Fix Hijri offset of 0 in options not overriding the value from the config entry
- Cancel the Next Prayer, Hijri and midnight timers on unload/reload (no duplicate timers)
- Remove the redundant "Prayer Midnight Refresh" sensor
- Log a warning when the schedule has no row for today
- Document which years the bundled schedule covers

## 1.0.4
- Reload the entry when options change so new settings apply immediately.

## 1.0.5
- Fix Hijri offset: shift the Gregorian date before converting so the month rolls over correctly (no "0 Muharram" or "31 Safar")
- Fix the same in the config and options preview
