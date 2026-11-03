"""Apple TV Users: switch an Apple TV's user from Home Assistant.

Home Assistant's Apple TV integration connects to each Apple TV with pyatv, which can list
and switch the TV's user accounts over the Companion protocol, but the integration doesn't
offer it. This adds a "User" select to each Apple TV, using the integration's own connection,
and a "Siri" button (the Siri Remote's), which pyatv has but neither it nor the integration offers.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

PLATFORMS = [Platform.BUTTON, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
