"""A "Siri" button for each Apple TV: the Siri Remote's Siri button, over the Companion protocol.

pyatv's Companion protocol has the Siri button (HidCommand.Siri) but no remote-control call for
it, and the Apple TV integration doesn't offer it. A press opens Siri on the TV; it listens
through the Siri Remote, not through whatever pressed the button.
"""

from __future__ import annotations

from typing import Any

from pyatv.const import Protocol
from pyatv.protocols.companion.api import HidCommand

from homeassistant.components.apple_tv.const import SIGNAL_CONNECTED, SIGNAL_DISCONNECTED
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .common import AppleTV, apple_tvs, remove_leftovers


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Any) -> None:
    buttons = [AppleTVSiriButton(tv) for tv in apple_tvs(hass)]
    remove_leftovers(hass, entry, "button", {button.unique_id for button in buttons if button.unique_id})
    async_add_entities(buttons)


class AppleTVSiriButton(ButtonEntity):
    _attr_icon = "mdi:microphone"
    _attr_should_poll = False

    def __init__(self, tv: AppleTV) -> None:
        self._tv = tv
        self._attr_unique_id = f"{tv.identifier}_siri"
        self._attr_name = f"{tv.name} Siri"
        # named after the TV's media player, like the select: button.<object id>_siri
        self.entity_id = f"button.{tv.object_id}_siri"
        self._attr_extra_state_attributes = {"media_player": tv.player}

    @property
    def available(self) -> bool:
        return self._tv.atv is not None

    async def async_added_to_hass(self) -> None:
        for signal in (SIGNAL_CONNECTED, SIGNAL_DISCONNECTED):
            self.async_on_remove(async_dispatcher_connect(self.hass, f"{signal}_{self._tv.identifier}", self._changed))

    @callback
    def _changed(self, *_: Any) -> None:
        self.async_write_ha_state()

    async def async_press(self) -> None:
        atv = self._tv.atv
        if atv is None:
            raise HomeAssistantError("The Apple TV isn't connected")
        # every Companion handler holds the Companion API; user accounts is one of them
        companion = atv.user_accounts.get(Protocol.Companion)
        if companion is None:
            raise HomeAssistantError("The Apple TV isn't paired for the Companion protocol")
        try:
            # a tap, as pyatv presses its other buttons
            await companion.api.hid_command(True, HidCommand.Siri)
            await companion.api.hid_command(False, HidCommand.Siri)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Couldn't press Siri: {err}") from err
