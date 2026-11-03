"""A "User" select for each Apple TV."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.apple_tv.const import SIGNAL_CONNECTED, SIGNAL_DISCONNECTED
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .common import AppleTV, apple_tvs, remove_leftovers

_LOGGER = logging.getLogger(__name__)

# accounts are added and removed rarely: read them on each connect and now and then
REFRESH_EVERY = timedelta(hours=6)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Any) -> None:
    selects = [AppleTVUserSelect(tv) for tv in apple_tvs(hass)]
    remove_leftovers(hass, entry, "select", {select.unique_id for select in selects if select.unique_id})
    async_add_entities(selects)


class AppleTVUserSelect(SelectEntity, RestoreEntity):
    """The Apple TV's users. pyatv can't say which one is current, so this shows the one last
    switched to from Home Assistant (switching on the TV itself goes unnoticed).

    Not attached to the Apple TV's device: Home Assistant makes a second device of the same name
    for another integration's entity rather than joining the Apple TV integration's."""

    _attr_icon = "mdi:account-switch"
    _attr_should_poll = False

    def __init__(self, tv: AppleTV) -> None:
        self._tv = tv
        self._identifier = tv.identifier
        self._accounts: dict[str, str] = {}
        self._attr_unique_id = f"{self._identifier}_user"
        self._attr_name = f"{tv.name} User"
        self._attr_options = []
        self._attr_current_option = None
        # named after the TV's media player, so apps can find it: select.<object id>_user
        self.entity_id = f"select.{tv.object_id}_user"
        self._attr_extra_state_attributes = {"media_player": tv.player}

    @property
    def _atv(self) -> Any:
        return self._tv.atv

    @property
    def available(self) -> bool:
        return self._atv is not None and bool(self._attr_options)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._attr_options = list(last.attributes.get("options") or [])
            if last.state in self._attr_options:
                self._attr_current_option = last.state
        self.async_on_remove(
            async_dispatcher_connect(self.hass, f"{SIGNAL_CONNECTED}_{self._identifier}", self._connected)
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, f"{SIGNAL_DISCONNECTED}_{self._identifier}", self._disconnected)
        )
        self.async_on_remove(async_track_time_interval(self.hass, self._refresh_now, REFRESH_EVERY))
        if self._atv is not None:
            self.hass.async_create_task(self._refresh())

    @callback
    def _connected(self, _atv: Any) -> None:
        self.hass.async_create_task(self._refresh())

    @callback
    def _disconnected(self) -> None:
        self.async_write_ha_state()

    @callback
    def _refresh_now(self, _now: datetime) -> None:
        self.hass.async_create_task(self._refresh())

    async def _refresh(self) -> None:
        atv = self._atv
        if atv is None:
            return
        try:
            accounts = await atv.user_accounts.account_list()
        except Exception as err:  # noqa: BLE001 - pyatv raises its own errors, timeouts and OSError
            _LOGGER.debug("Couldn't read the users of %s: %s", self._identifier, err)
            self.async_write_ha_state()
            return
        self._accounts = {account.name: account.identifier for account in accounts}
        self._attr_options = list(self._accounts)
        if self._attr_current_option not in self._attr_options:
            self._attr_current_option = None
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        atv = self._atv
        if atv is None:
            raise HomeAssistantError("The Apple TV isn't connected")
        if option not in self._accounts:
            await self._refresh()
        if (account_id := self._accounts.get(option)) is None:
            raise HomeAssistantError(f"The Apple TV has no user called {option}")
        try:
            await atv.user_accounts.switch_account(account_id)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Couldn't switch the Apple TV to {option}: {err}") from err
        self._attr_current_option = option
        self.async_write_ha_state()
