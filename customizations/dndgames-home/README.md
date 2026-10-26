# Editable Home theme source

The source files here are the v2.2 presentation delta. Do not overwrite newer upstream Home HTML with the old generated TV package.

- `source/stacked.css`: bottom stacking, compact clock, tile styling.
- `source/original-scroll.js`: reviewed upstream scrollTrack function, used as a compatibility guard.
- `source/stacked-scroll.js`: short-row centring while keeping long-track scrolling.
- `source/clean-weather.css`: label visibility and final clock/weather positions.
- `source/weather-card.html`: visible town/country and weather markup/attribution.
- `source/weather.js`: independent HTTPS weather widget, fixed Staines location, cache/refresh/error handling.
- `build.py`: narrow source transformer and generated-output check.
- `tests/`: local source tests, with an MIT upstream HTML fixture, NOT a deployment template.

From the repository root:

```bash
python3 customizations/dndgames-home/build.py check server/assets/home.html
python3 customizations/dndgames-home/tests/test_theme.py
```

After editing theme source, generate a separate candidate before replacing the served source:

```bash
python3 customizations/dndgames-home/build.py build server/assets/home.html /tmp/glasshouse-home-candidate.html
```

The output path must not already exist. Review the diff and run upstream/browser tests before replacing `server/assets/home.html`. The builder can strip its own marked additions and reapply source, but refuses older unmarked one-off custom patches. Preserve the upstream source as supplied by your chosen commit.

Python 3.10+ is required for the update kit. Node.js is required by its JavaScript syntax checks. Existing server runtime requirements are unchanged. The kit does not install development dependencies or run unreviewed package-manager hooks for you.
