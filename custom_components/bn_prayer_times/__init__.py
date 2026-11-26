from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import PrayerCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BN Prayer Times from a config entry."""

    coordinator = PrayerCoordinator(hass, entry)

    # store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # FIRST refresh (required by HA)
    await coordinator.async_config_entry_first_refresh()

    # ⭐ EXTRA startup refresh safeguard
    # ensures data is correct immediately after HA restart
    await coordinator.async_request_refresh()

    # forward platforms
    await hass.config_entries.async_forward_entry_setups(
        entry,
        ["sensor"],
    )

    # reload the entry when the options are changed
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    
    return True

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry so new options take effect immediately."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        ["sensor"],
    )

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        # cancel the coordinator's midnight timer
        await coordinator.async_shutdown()

    return unload_ok
