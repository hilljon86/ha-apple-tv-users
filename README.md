# Apple TV Users

Switch an Apple TV's user from Home Assistant.

Home Assistant's [Apple TV integration](https://www.home-assistant.io/integrations/apple_tv) connects to each Apple TV with [pyatv](https://pyatv.dev), which can list and switch the TV's user accounts over the Companion protocol, but the integration doesn't offer it. This custom integration adds a **User** select to each Apple TV's device, using the Apple TV integration's own connection (nothing to pair).

- The select is named after the TV's media player: `media_player.bedroom_apple_tv` gets `select.bedroom_apple_tv_user`, with the media player in its `media_player` attribute.
- Its options are the TV's users, read when the TV connects and every six hours.
- Choosing one switches the TV (`select.select_option`).
- pyatv can't tell which user is current, so the select shows the one last switched to from Home Assistant. Switching on the TV itself goes unnoticed.

## Install

With HACS: add this repository as a custom repository (category Integration), download Apple TV Users, restart Home Assistant, then add the Apple TV Users integration under Settings > Devices & services.

By hand: copy `custom_components/apple_tv_users` into your config's `custom_components` folder and do the same.

The Apple TV needs to be paired with the Companion protocol (Home Assistant pairs it when you set up the Apple TV integration).
