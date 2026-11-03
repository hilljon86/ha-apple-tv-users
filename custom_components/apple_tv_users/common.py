"""What the select and the button share: finding the Apple TVs, and the Companion connection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.apple_tv.const import DOMAIN as APPLE_TV_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


@dataclass
class AppleTV:
    entry: ConfigEntry
    identifier: str
    #: its media player, which names the entities: media_player.porch gets select.porch_user
    player: str
    name: str

    @property
    def object_id(self) -> str:
        return self.player.split(".", 1)[1]

    @property
    def atv(self) -> Any:
        """The Apple TV integration's pyatv connection, None while it's disconnected."""
        return getattr(getattr(self.entry, "runtime_data", None), "atv", None)


def apple_tvs(hass: HomeAssistant) -> list[AppleTV]:
    """The Apple TV integration's Apple TVs (it also has HomePods and AirPort Expresses)."""
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    tvs = []
    for entry in hass.config_entries.async_entries(APPLE_TV_DOMAIN):
        if entry.unique_id is None or entry.disabled_by is not None:
            continue
        player = entities.async_get_entity_id("media_player", APPLE_TV_DOMAIN, entry.unique_id)
        device = devices.async_get_device(identifiers={(APPLE_TV_DOMAIN, entry.unique_id)})
        if player is None or device is None or "Apple TV" not in (device.model or ""):
            continue
        tvs.append(AppleTV(entry, entry.unique_id, player, device.name_by_user or device.name or entry.title))
    return tvs


def remove_leftovers(hass: HomeAssistant, entry: ConfigEntry, domain: str, keep: set[str]) -> None:
    """0.1.0 left a device per Apple TV entry and selects for HomePods: drop what isn't made now."""
    entities = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entities, entry.entry_id):
        if entity.domain == domain and entity.unique_id not in keep:
            entities.async_remove(entity.entity_id)
    devices = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(devices, entry.entry_id):
        devices.async_update_device(device.id, remove_config_entry_id=entry.entry_id)
