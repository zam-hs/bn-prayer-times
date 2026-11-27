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

##1.0.6
- Faster and lighter: prayers.csv is read once, today/tomorrow times are calculated once per refresh (no per-sensor parsing)
- Entities only update when the data actually changes
- Midnight refresh is immediate and uses a single recurring local-midnight timer
- Next Prayer and Hijri timers are now plain callbacks (no per-second task creation)
- The Next Prayer countdown attribute is no longer written to the database
- Hijri Date now updates exactly at the real Maghrib time (it could be a minute early before)
- Next Prayer shows nothing, instead of a stale prayer, when no schedule is left
- Invalid times in prayers.csv are skipped with a warning instead of raising errors
- Remove the redundant second refresh at startup
- Move Hijri helpers to their own module and share one schema/preview in the config flow
- Use entry.runtime_data and pass config_entry to the coordinator
- Minimum Home Assistant version is now 2024.11.0 (needed by the options flow and coordinator changes)
- Remove unused content_in_root from hacs.json and a stray images/.screenshot file
