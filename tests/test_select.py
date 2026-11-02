"""The User select, against a stand-in for the Apple TV integration's pyatv connection."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pyatv.interface import UserAccount

from homeassistant.components.apple_tv.const import DOMAIN as APPLE_TV_DOMAIN, SIGNAL_DISCONNECTED
from homeassistant.components.select import ATTR_OPTION, ATTR_OPTIONS, DOMAIN as SELECT_DOMAIN, SERVICE_SELECT_OPTION
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.apple_tv_users.const import DOMAIN

TV_ID = "4E:43:10:4C:9B:81"
SELECT = "select.bedroom_apple_tv_user"


class FakeAccounts:
    def __init__(self) -> None:
        self.account_list = AsyncMock(return_value=[UserAccount("Jon", "id-jon"), UserAccount("Kids", "id-kids")])
        self.switch_account = AsyncMock()


async def set_up(hass: HomeAssistant) -> SimpleNamespace:
    # the Apple TV integration needs zeroconf, which would open sockets
    hass.config.components.add("zeroconf")
    tv_entry = MockConfigEntry(domain=APPLE_TV_DOMAIN, unique_id=TV_ID, title="Bedroom Apple TV")
    tv_entry.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(config_entry_id=tv_entry.entry_id, identifiers={(APPLE_TV_DOMAIN, TV_ID)},
                                           name="Bedroom Apple TV")
    er.async_get(hass).async_get_or_create("media_player", APPLE_TV_DOMAIN, TV_ID, suggested_object_id="bedroom_apple_tv",
                                           config_entry=tv_entry)
    accounts = FakeAccounts()
    manager = SimpleNamespace(atv=SimpleNamespace(user_accounts=accounts))
    tv_entry.runtime_data = manager
    entry = MockConfigEntry(domain=DOMAIN, title="Apple TV Users")
    entry.add_to_hass(hass)
    # the Apple TV integration's own setup would connect to a real TV
    with patch("homeassistant.components.apple_tv.async_setup_entry", return_value=True):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return SimpleNamespace(accounts=accounts, manager=manager)


async def test_lists_and_switches_users(hass: HomeAssistant) -> None:
    tv = await set_up(hass)
    state = hass.states.get(SELECT)
    assert state is not None
    assert state.attributes[ATTR_OPTIONS] == ["Jon", "Kids"]
    assert state.attributes["media_player"] == "media_player.bedroom_apple_tv"
    # pyatv can't say who's on: unknown until switched from here
    assert state.state == STATE_UNKNOWN
    assert state.name == "Bedroom Apple TV User"

    await hass.services.async_call(SELECT_DOMAIN, SERVICE_SELECT_OPTION, {ATTR_ENTITY_ID: SELECT, ATTR_OPTION: "Kids"},
                                   blocking=True)
    tv.accounts.switch_account.assert_awaited_once_with("id-kids")
    assert hass.states.get(SELECT).state == "Kids"


async def test_unavailable_while_the_tv_is_disconnected(hass: HomeAssistant) -> None:
    tv = await set_up(hass)
    tv.manager.atv = None
    async_dispatcher_send(hass, f"{SIGNAL_DISCONNECTED}_{TV_ID}")
    await hass.async_block_till_done()
    assert hass.states.get(SELECT).state == STATE_UNAVAILABLE


async def test_a_failed_switch_says_so(hass: HomeAssistant) -> None:
    tv = await set_up(hass)
    tv.accounts.switch_account.side_effect = OSError("timed out")
    with pytest.raises(HomeAssistantError, match="Couldn't switch the Apple TV to Jon"):
        await hass.services.async_call(SELECT_DOMAIN, SERVICE_SELECT_OPTION, {ATTR_ENTITY_ID: SELECT, ATTR_OPTION: "Jon"},
                                       blocking=True)
    assert hass.states.get(SELECT).state == STATE_UNKNOWN
