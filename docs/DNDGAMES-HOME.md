# D&D Games Home Edition v2.2

A presentation customisation of Glasshouse Home maintained in the wkirby86/glasshouse fork. It is not affiliated with the upstream maintainer and does not replace the rooted TV's underlying LG firmware.

## Differences from stock Home

| Area | Home edition |
| --- | --- |
| App/input rows | Bottom-stacked; short rows centred; longer rows retain scrolling |
| Clock/date | Smaller, top right, right-aligned |
| Weather | Top-left card for Staines-upon-Thames, UK; Celsius, mph, Europe/London |
| Row headings | Hidden in normal viewing; restored in Arrange mode because they contain sorting controls |
| Tiles | Rounded, translucent panels with focus using the configured accent colour |
| Last-opened / picture-information panel | Hidden visually, not deleted from the DOM |
| Wallpaper | Existing Glasshouse time slots and uploaded pictures retained; no photos included |
| Hidden apps | Existing filtering retained; Arrange mode still intentionally reveals hidden tiles |
| Home takeover, server routes, privacy controls | Not changed by this customisation |

The saved row order is respected. To place Inputs above Apps, use the existing arrangement controls. The theme does not rewrite home.json or choose the user's pinned applications.

## Weather, privacy and limitations

Weather comes from direct HTTPS calls to Open-Meteo. No account/key is embedded. Normal refresh is every 15 minutes while visible; retry and labelled cached-data fallbacks remain in the widget. The core launcher should keep working during a forecast failure. External service availability, TLS and CORS support still need checking on the target TV.

There is **no location picker, automatic geolocation or dashboard weather toggle**. Staines is a town-centre coordinate, not a residential address. To change location, edit the coordinates/timezone/cache key in `customizations/dndgames-home/source/weather.js` and the visible labels in `source/weather-card.html`, rebuild and test. Merely changing a README or manifest label does not change the forecast.

The provider sees the requested location and public connection IP. No Glasshouse token, app list or private wallpaper is supplied by the widget. Attribution appears in the card: Open-Meteo / CC BY 4.0. See https://open-meteo.com/en/docs and https://open-meteo.com/en/terms for service conditions; the free endpoint is not a blanket commercial-use entitlement.

## Development and review

Use a feature branch; keep the upstream `LICENSE` and other authors' notices. Theme source lives in `customizations/dndgames-home/source`. `server/assets/home.html` remains the served, self-contained view.

The builder makes narrow additions to the current checkout rather than replacing it with a generated file from an older server. It stops when the reviewed scroll function or required DOM/style hooks differ. A clean source transformation is NOT proof that newer upstream code is behaviourally compatible. Run this checkout's upstream tests, the custom source tests and a browser/TV acceptance test before merging or releasing.

The integration adds no server runtime dependency and changes no backend or takeover file. It does not update upstream package.json version, release workflow, updater endpoint or GitHub Pages configuration. Upstream updates or redeployment can overwrite a local TV patch; maintain the fork and review future diffs.

## Deploy and reload

Do not deploy a newly ported fork merely because the Git check passed. Review and test it first using that checkout's own installation documentation. Never copy your whole `/var/lib/tvweb` directory to GitHub.

The installed v0.118.0 setup in the development conversation needed a **full system reboot** to clear the running HTML/server cache after a file change. Returning to Home was not enough. Use the known Homebrew system reboot only when ready; no automated TV commands are included in this repository update kit.

## Acceptance checklist

- Clock/date top right, weather top left; no overlapping dock or portrait.
- Apps and Inputs stay bottom-centred; long rows scroll to the focused tile.
- Normal view respects hidden applications and the saved row order.
- Arrange shows its heading/sort controls and hidden tiles, then saves normally.
- Pointer, arrows, short/long OK, Back, recents and app/input launch still work.
- Weather handles success, no network, timeout and stale cache without breaking Home.
- Pressing Home from an app and after a full reboot uses the existing takeover.

## Rollback

For unpublished source changes, use Git to restore only the reviewed paths, or discard the dedicated fresh working copy after preserving any new work. After a published commit, prefer a `git revert` commit over rewriting shared history. This source kit does not alter your TV. A deployed television needs its own backed-up Home file restored and a reload/reboot as appropriate.

## Attribution

Glasshouse: https://github.com/rorygallagher2024/glasshouse (MIT; original notices retained). Weather: Open-Meteo and CC BY 4.0. No private images, fonts, credentials, TV configuration or installation-state files are included by this customisation.
