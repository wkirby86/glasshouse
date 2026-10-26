# D&D Games Home customisation v2.3

Editable Home-view additions; upstream backend and takeover remain untouched.

`source/stacked.css` and `stacked-scroll.js` retain the reviewed dock.
`source/clean-weather.css` styles the card and location dialog.
`source/weather-card.html` contains the card and accessible dialog.
`source/weather.js` implements search, validation, local preferences and weather.
`source/weather-key-hook.js` is the narrow bridge from Up at the top dock row to Change.

Run from repository root:

```sh
python3 customizations/dndgames-home/build.py check server/assets/home.html
python3 customizations/dndgames-home/tests/test_theme.py
```

After source edits, generate to a distinct file, review, then replace the served HTML:

```sh
python3 customizations/dndgames-home/build.py build server/assets/home.html /tmp/home-reviewed.html
```

The builder removes its own delimited previous additions before rebuilding, preserving the current upstream baseline. It can migrate the known v2.2 envelope; incompatible key/scroll/DOM changes cause a stop. Never copy an old generated Home page over a new upstream checkout.

Optional browser tests: install Playwright in a separate virtual environment and provide Chromium, then run `tests/location_browser_test.py`. It uses mocked APIs/storage, not a real TV or live weather. Results are written beneath ignored `tests/_test-output`.

See `../../docs/DNDGAMES-HOME.md` for UI, privacy and deployment limitations. Original MIT licence retained.
