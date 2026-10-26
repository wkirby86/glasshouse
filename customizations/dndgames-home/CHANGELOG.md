# Home-theme changes

## v2.3 - Selectable weather location

- Add explicit town/postcode search and region/country result selection.
- Save location in the TV Home view's localStorage; current Staines default retained.
- Per-location cache, request cancellation and stale-response guards.
- Add pointer/keyboard/remote access without altering root, backend or takeover.
- Preserve v2.2 layout and hidden app selections.
- No optional weather enable/disable control in this release.

# D&D Games Home change history

These are Home customisation versions, not upstream Glasshouse server releases.

## 2.2 - clock/weather swap

- Weather card moved from the top right to the top left.
- Clock and date moved from the top left to the top right and right-aligned.
- Staines-upon-Thames location, units, refresh/cache behaviour and forecast attribution unchanged.
- Existing dock, hidden-app filters, wallpapers and Home takeover retained.
- Fork integration adds editable source, reversible source generation, tests, documentation and a review plan.

## 2.1 - clean headings and weather

- Hide Apps/Inputs labels and counts in normal viewing, retain controls during Arrange.
- Add model-based current weather and a three-day outlook via Open-Meteo.
- Add labelled cached/unavailable states and independent weather refresh logic.

## 2.0 - stacked Home presentation

- Bottom-align the rows and centre tracks only when their tiles fit.
- Retain scrolling for longer rows and arrangement-mode behaviour.
- Compact clock, hide the large last-opened panel, and use rounded translucent tiles.

## Validation boundary

The earlier custom layout and weather were confirmed working by the TV owner. That is not a claim that a newly ported fork or v2.2 has passed physical-TV acceptance. This kit's test report covers local source transformation and guard behaviour only. Run the target checkout's own tests and document hardware acceptance before a public release.
