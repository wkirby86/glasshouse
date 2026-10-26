#!/usr/bin/env python3
"""Source regressions for the weather i18n/focus fixes; not the upstream CI runner."""
import importlib.util
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('theme_build_ci', ROOT / 'build.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

class MarkupAudit(HTMLParser):
    """Small independent check of the documented static-string contract."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.problems, self.elements, self.strings = [], [], {}, {}
    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        entry = [tag, attrs, []]
        if attrs.get('id'): self.elements[attrs['id']] = entry
        for name in ('aria-label', 'title', 'placeholder'):
            value = attrs.get(name, '')
            if re.search('[A-Za-z]', value):
                key = attrs.get('data-t-' + name)
                if not key: self.problems.append((tag, name, value))
                else: self.strings[key] = value
        if tag not in ('input', 'img', 'meta', 'link', 'br', 'hr'): self.stack.append(entry)
    def handle_data(self, text):
        if self.stack: self.stack[-1][2].append(text)
        if re.search('[A-Za-z]', text) and self.stack and not self.stack[-1][1].get('data-t'):
            self.problems.append((self.stack[-1][0], 'text', text))
    def handle_endtag(self, tag):
        if self.stack and self.stack[-1][0] == tag:
            _, attrs, parts = self.stack.pop()
            if attrs.get('data-t'): self.strings[attrs['data-t']] = ''.join(parts).strip()

def markup():
    p = MarkupAudit()
    p.feed(b.source('weather-card.html'))
    return p

class CICompatibilityTests(unittest.TestCase):
    def test_static_text_and_attributes_have_keys(self):
        self.assertEqual(markup().problems, [])
    def test_place_names_are_dynamic_data(self):
        p = markup()
        for ident in ('dnd-wx-place', 'dnd-wx-country'):
            entry = p.elements[ident]
            self.assertNotIn('data-t', entry[1])
            self.assertEqual(''.join(entry[2]), '\u2014')
    def test_script_owned_fields_have_placeholders_not_static_keys(self):
        p = markup()
        for ident in ('dnd-wx-condition', 'dnd-wx-feels', 'dnd-wx-detail', 'dnd-wx-stamp'):
            self.assertNotIn('data-t', p.elements[ident][1])
            self.assertEqual(''.join(p.elements[ident][2]), '\u2014')
    def test_dynamic_sentences_use_literal_translation_keys(self):
        js = b.source('weather.js')
        for key in ('forLocation', 'currentLocation', 'selectedLocation', 'modelTitle', 'feelsLike', 'windMph', 'cachedAt', 'updatedAt'):
            self.assertIn("t('home.weather." + key + "',", js)
        self.assertNotIn("'Weather for ' +", js)
        self.assertNotIn("'Selected: ' +", js)
    def test_translation_keys_have_consistent_english(self):
        strings = markup().strings
        pattern = re.compile(r"\bt\('([^']+)',\s*'((?:[^'\\]|\\.)*)'")
        for key, value in pattern.findall(b.source('weather.js')):
            value = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m[1], 16)), value)
            if key in strings: self.assertEqual(strings[key], value, key)
            strings[key] = value
            self.assertRegex(key, r'^home\.weather\.[a-z][a-zA-Z0-9]*$')
        self.assertGreaterEqual(len(strings), 50)
    def test_no_shadowed_translator(self):
        self.assertNotRegex(b.source('weather.js'), r'\b(?:var|function)\s+t\b')
    def test_stock_app_focus_outline_is_not_overridden(self):
        rule = re.search(r'\.tile\.focus\{([^}]*)\}', b.source('stacked.css'))[1]
        self.assertNotIn('outline', rule)
    def test_generated_html_has_fixed_source_and_core_roundtrips(self):
        stock = (ROOT/'tests/fixtures/home-stock.html').read_text()
        generated = b.add_theme(stock)
        self.assertEqual(b.verify(generated), stock)
        self.assertIn('data-t="home.weather.change"', generated)
        self.assertNotIn('.tile.focus{background:rgba(34,25,48,.86);outline-color:#e9ad55}', generated)
    def test_protocol_and_persistence_values_preserved(self):
        js = b.source('weather.js')
        for value in ("'dnd.glasshouse.weather.settings.v1'", "'Europe/London'", "'Staines-upon-Thames'", 'wind_speed_unit=mph', 'language=en&format=json'):
            self.assertIn(value, js)

if __name__ == '__main__':
    unittest.main(verbosity=2)
