## Summary

Integrate D&D Games Home Edition v2.2 into this fork while retaining upstream Glasshouse backend, privacy tooling and Home takeover.

## Changes

- Bottom-stacked dock with centred short tracks and existing long-track scrolling.
- Compact top-right clock/date and top-left Staines-upon-Thames weather.
- Hide normal-view row headings, keeping Arrange controls and hidden-app filtering.
- Rounded translucent tiles; hide the large last-opened panel.
- Add maintainable source, build checks, local tests, README introduction and change history.

## Deliberately unchanged

Backend APIs, Home takeover, app launch handlers, persisted home.json, installed wallpapers, privacy settings, upstream licence, package/server version and release/update workflows.

## Known limitations

Weather is fixed to Staines-upon-Thames (Celsius/mph/Europe-London); no location selector is included. Forecasts contact Open-Meteo and require internet access. Existing Home takeover compatibility constraints still apply. Newer upstream baselines require source, browser and hardware review.

## Validation - fill in before marking ready

- [ ] Inspect full source diff and recorded base commit.
- [ ] Custom build consistency check and source tests pass.
- [ ] Target checkout's upstream test/lint/security checks pass.
- [ ] Browser tests cover navigation, overflow, Arrange, hidden items and weather failures.
- [ ] Physical-TV tests cover Home button, app/input launch and full reboot.
- [ ] No private photos, configuration, tokens, SSH material or test credentials staged.

Target this pull request at **wkirby86/glasshouse**, not the upstream maintainer's repository, unless separately agreed.
