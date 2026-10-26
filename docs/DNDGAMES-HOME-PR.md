# Home v2.3: selectable weather location

## Summary
A Home-screen presentation enhancement: add Change location to the existing weather card. Search a town/postcode, choose a region/country match, then save. Staines stays the default. No backend, Home takeover or firmware changes.

## Changes
- Search dialog, explicit save/cancel, keyboard/pointer/remote controls.
- Per-Home-webview local preference and coordinate/timezone-specific cache.
- Request cancellation and generation guards prevent old results overwriting a new location.
- Offline, invalid data, storage denial, rate-limit and no-result handling.
- Top-right clock, top-left weather, dock, hidden-item filtering and wallpapers retained.
- README/docs updated; location is no longer described as fixed.

## Validation
- Source round-trip/preservation tests and mocked-browser regression suite included.
- Review the updater's changes.patch and run this checkout's upstream test suite.
- [ ] Physical LG TV: on-screen keyboard, remote navigation, search/save and reboot persistence.
- [ ] App/HDMI launching, hidden apps, Arrange, Recents and Home takeover verified.

## Limitations
Storage is local to the TV Home webview, not synced with a PC dashboard or stored in home.json. Clearing webview storage resets the default. Postcode coverage depends on the search provider. External search/weather requests require internet. No weather on/off toggle is added. Do not label this a backend or firmware upgrade; v2.3 is the Home-theme version.
