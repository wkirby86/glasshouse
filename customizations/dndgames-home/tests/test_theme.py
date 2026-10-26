#!/usr/bin/env python3
"""Offline source-preservation/guard tests. Does not connect to a television."""
import importlib.util
import re
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('theme_build', ROOT / 'build.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
STOCK = (ROOT / 'tests/fixtures/home-stock.html').read_bytes().decode('utf-8')

class ThemeTests(unittest.TestCase):
    def test_roundtrip(self):
        self.assertEqual(b.strip_theme(b.add_theme(STOCK)), STOCK)
    def test_verify(self):
        self.assertEqual(b.verify(b.add_theme(STOCK)), STOCK)
    def test_new_upstream_code_preserved(self):
        changed = STOCK.replace('  function refreshGuide() {', '  // Example later upstream change\n  function refreshGuide() {')
        self.assertEqual(b.strip_theme(b.add_theme(changed)), changed)
    def test_changed_scroll_refused(self):
        with self.assertRaises(ValueError): b.add_theme(STOCK.replace('wrap.clientWidth - 44', 'wrap.clientWidth - 50'))
    def test_existing_customization_refused(self):
        with self.assertRaises(ValueError): b.add_theme(b.add_theme(STOCK))
    def test_missing_stage_refused(self):
        with self.assertRaises(ValueError): b.add_theme(STOCK.replace('id="stage"', 'id="another-stage"'))
    def test_duplicate_rows_refused(self):
        with self.assertRaises(ValueError): b.add_theme(STOCK.replace('</body>', '<main id="rows"></main></body>'))
    def test_changed_styles_refused(self):
        with self.assertRaises(ValueError): b.add_theme(STOCK.replace('#rows{position:', '#new-rows{position:'))
    def test_hidden_filter_retained(self):
        self.assertIn('if (it && (state.arranging || !hidden(kind, id))) out.push(it);', b.add_theme(STOCK))
    def test_look_colour_runtime_retained(self):
        text = b.add_theme(STOCK)
        self.assertIn("var LOOK = $('look').textContent", text)
        self.assertLess(text.index('DNDGAMES-CLOCK-WEATHER-V22'), text.index("var LOOK = $('look').textContent"))
    def test_positions(self):
        text = b.add_theme(STOCK)
        self.assertIn('left:90px;right:auto;width:438px', text)
        self.assertIn('margin-left:auto;text-align:right', text)
    def test_existing_referrer_preserved(self):
        changed = STOCK.replace('<head>', '<head>\n<meta name="referrer" content="same-origin">')
        self.assertEqual(b.strip_theme(b.add_theme(changed)), changed)
    def test_weather_single_instance(self):
        text = b.add_theme(STOCK)
        self.assertEqual(text.count('id="dnd-weather"'), 1)
        self.assertEqual(text.count('function forecastURL(p)'), 1)
    def test_headings_only_hidden_in_normal_mode(self):
        text = b.add_theme(STOCK)
        self.assertIn('#stage:not(.arranging) #rows .row > h2{display:none}', text)
        self.assertIn('#stage.arranging #rows .row > h2{display:block}', text)
    def test_mismatched_markers_refused(self):
        changed = b.add_theme(STOCK).replace(b.CSS_END, '')
        with self.assertRaises(ValueError): b.strip_theme(changed)
    def test_manual_css_edit_detected(self):
        changed = b.add_theme(STOCK).replace('right:auto;width:438px', 'right:auto;width:999px')
        with self.assertRaises(ValueError): b.verify(changed)
    def test_launcher_roundtrip_restores_scroll_and_weather_focus_hook(self):
        text = b.add_theme(STOCK)
        restored = b.strip_theme(text)
        scripts = lambda s: re.findall(r'<script(?:\s[^>]*)?>([\s\S]*?)</script>', s)
        self.assertEqual(scripts(restored), scripts(STOCK))

class LocationSourceTests(unittest.TestCase):
    def test_location_dialog_single_instance(self):
        text=b.add_theme(STOCK)
        self.assertEqual(text.count('id="dnd-weather-settings"'),1)
        self.assertEqual(text.count('id="dnd-wx-change"'),1)
    def test_minimal_key_bridge_exists(self):
        text=b.add_theme(STOCK)
        self.assertEqual(text.count('window.DNDWeatherLocation.focusControl()'),1)
        self.assertIn('!state.arranging && !recents.open && !recents.loading',text)
    def test_key_handler_change_is_guarded(self):
        changed=STOCK.replace('    var k = e.keyCode;', '    var k = Number(e.keyCode);')
        with self.assertRaises(ValueError): b.add_theme(changed)
    def test_new_weather_does_not_post_backend(self):
        js=b.source('weather.js')
        self.assertNotIn('/api/home/layout',js)
        self.assertNotIn("open('POST'",js)
        self.assertNotIn('navigator.geolocation',js)
    def test_race_guards_present(self):
        js=b.source('weather.js')
        self.assertIn('token !== generation',js)
        self.assertIn('token !== searchRevision',js)
    def test_provider_strings_are_not_html(self):
        js=b.source('weather.js')
        self.assertIn('title.textContent = p.name',js)
        self.assertIn('safeText(p.name, 120)',js)
    def test_search_separate_from_forecast(self):
        js=b.source('weather.js')
        self.assertIn('geocoding-api.open-meteo.com/v1/search?name=',js)
        self.assertIn('api.open-meteo.com/v1/forecast?latitude=',js)
    def test_storage_versioned_separately(self):
        js=b.source('weather.js')
        self.assertIn('dnd.glasshouse.weather.settings.v1',js)
        self.assertIn("cacheKey(location)",js)
    def test_current_javascript_parses(self):
        import subprocess, shutil
        if not shutil.which('node'): self.skipTest('Node.js unavailable')
        subprocess.run(['node','--check',str(ROOT/'source/weather.js')],check=True,capture_output=True)

if __name__ == '__main__': unittest.main(verbosity=2)
