# D&D Games Home Edition v2.3

Aesthetic changes to the Glasshouse Home screen, with a configurable weather card. This fork is not an official upstream release and does not replace webOS. Glasshouse's backend, privacy controls, app catalogue, hidden-item settings and Home takeover remain intact. A small remote-focus bridge is added to the Home view; this is not a claim of zero interaction changes.

## Change the weather location

On the **TV's Glasshouse Home**, select **Change** in the weather card. Enter a town or postcode, press **Search**, choose the result with the correct region and country, then choose **Save location**. Search results come from Open-Meteo/GeoNames; postcode coverage varies, so try the nearest town when a postcode returns nothing. There is no automatic geolocation and no sign-in/API key embedded in the source.

- Magic Remote pointer/mouse: click Change and the form controls.
- Directional remote: Up from the top visible dock row highlights Change; OK opens settings. Blue is a shortcut outside Arrange/Recents.
- In the dialog: arrows navigate buttons/results, OK selects, Back/Escape cancels. Enter in the search field searches. A keyboard or the TV's on-screen text input enters the query. Actual webOS on-screen keyboard behaviour requires device testing.
- Selecting a result is not a save. Cancel leaves the current location unchanged.
- Existing Staines users stay on Staines unless they save a different result. Units remain Celsius and mph; the selected location supplies its forecast timezone. The TV clock itself is unchanged.

## Persistence and privacy

Location is saved in **localStorage belonging to the Home view on that TV**, under `dnd.glasshouse.weather.settings.v1`. It is NOT written to `home.json`, the dashboard configuration, Git or a cloud account. Changing location in a browser on your PC only changes that browser's storage, not the television. Clearing the Home webview's data, reinstalling its web app or changing its origin may reset the preference to Staines. Glasshouse server backups do not necessarily include this browser-local preference.

Forecasts are cached per coordinates/timezone/units. Saving a new location clears the old active forecast cache and invalidates in-flight requests before showing fresh data. Invalid stored data falls back to the default. A storage failure is shown explicitly rather than falsely claiming the setting was saved.

Open-Meteo receives the typed search and selected forecast coordinates, as well as the connection IP. The widget sends neither app lists, wallpaper images nor Glasshouse credentials; cross-site requests use no credential headers. Searches happen only on Search/Enter. Forecasts refresh every 15 minutes while visible, with retry/backoff and labelled stale data. Internet/TLS/CORS availability needs checking on the TV. The underlying launcher continues to operate if weather is unavailable.

Provider documentation: https://open-meteo.com/en/docs/geocoding-api and https://open-meteo.com/en/docs . Free endpoints are intended for non-commercial use; consult the provider's terms for distribution/use. Search data attribution: GeoNames. Forecast attribution: Open-Meteo / CC BY 4.0, retained in the card.

## Visual layout retained

Clock/date stay top right, weather top left, dock at the bottom. Row headings remain hidden normally and return in Arrange mode. Saved application visibility, row order, recents and wallpaper slots are preserved. The stock LG Home recovery tile remains available. No new server runtime dependency, service or boot hook is added.

## Build and test

```sh
python3 customizations/dndgames-home/build.py check server/assets/home.html
python3 customizations/dndgames-home/tests/test_theme.py
# Optional browser tests need Python Playwright and Chromium:
python3 customizations/dndgames-home/tests/location_browser_test.py
```

The builder uses the current checkout's Home source, with narrow reversible additions. It refuses changed/unrecognised DOM, scroll or key-handler anchors rather than substituting an older upstream file. Run the current repository's upstream tests as well before release.

## Deployment and acceptance

This source update does not deploy to the TV. The accompanying guarded `install_tv.py` is a separate opt-in local command with backups and rollback. After changing the installed HTML, perform a full system reboot to refresh the known running server/page cache; merely returning Home was insufficient on the installed setup.

Test on the television: Change reachable by pointer and remote; keyboard enters query; results distinguish duplicate towns; Cancel leaves current weather; Save changes actual forecast coordinates and labels; location survives full reboot; Home button, HDMI/app launching, hidden apps, Arrange and Recents still work. Local browser tests mock APIs and storage and do not certify physical TV compatibility.

## Scope and acknowledgement

This fork focuses on Home-screen aesthetics and the weather UI. It does not change LG firmware, rooting, entitlement handling, Glasshouse privacy services or the Home takeover. Original Glasshouse copyright/licence and credits are retained. There is no weather enable/disable toggle in this release.
