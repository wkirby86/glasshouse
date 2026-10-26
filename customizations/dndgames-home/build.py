#!/usr/bin/env python3
"""Port the reviewed presentation delta; never substitute an old full Home page."""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TAG = 'DNDGAMES-HOME-FORK-V22'
CSS_START = '\n/* ' + TAG + ' CSS BEGIN */\n'
CSS_END = '/* ' + TAG + ' CSS END */\n'
CARD_START = '<!-- ' + TAG + ' CARD BEGIN -->\n'
CARD_END = '<!-- ' + TAG + ' CARD END -->\n  '
JS_START = '<!-- ' + TAG + ' SCRIPT BEGIN -->\n<script>\n'
JS_END = '</script>\n<!-- ' + TAG + ' SCRIPT END -->\n'
SCROLL_START = '  /* ' + TAG + ' SCROLL BEGIN */\n'
SCROLL_END = '\n  /* ' + TAG + ' SCROLL END */'
META = '\n<!-- ' + TAG + ' PRIVACY -->\n<meta name="referrer" content="no-referrer">'


def source(name: str) -> str:
    return (ROOT / 'source' / name).read_text(encoding='utf-8')


def replace_once(text: str, old: str, new: str) -> str:
    if not old or text.count(old) != 1:
        raise ValueError('Expected source block not found exactly once: ' + old[:90])
    return text.replace(old, new, 1)


def remove_block(text: str, start: str, end: str, replacement: str = '') -> str:
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError('Incomplete or duplicated theme markers: ' + start.strip())
    a = text.index(start)
    b = text.index(end, a) + len(end)
    return text[:a] + replacement + text[b:]


def strip_theme(text: str) -> str:
    """Reverse only the delimited additions, keeping all other upstream bytes."""
    text = remove_block(text, CSS_START, CSS_END)
    text = remove_block(text, CARD_START, CARD_END)
    text = remove_block(text, JS_START, JS_END)
    text = remove_block(text, SCROLL_START, SCROLL_END, source('original-scroll.js').rstrip('\n'))
    if META in text:
        text = replace_once(text, META, '')
    if TAG in text:
        raise ValueError('Unexpected theme marker remains after removal.')
    return text


def add_theme(text: str) -> str:
    if any(x in text for x in (TAG, 'DNDGAMES-STACKED-V2', 'DNDGAMES-CLEAN-WEATHER-V21', 'id="dnd-weather"')):
        raise ValueError('This Home page is already customised; do not layer patches.')
    # The scroll function is the only upstream JavaScript function we replace.
    old_scroll = source('original-scroll.js').rstrip('\n')
    new_scroll = source('stacked-scroll.js').rstrip('\n')
    if text.count(old_scroll) != 1:
        raise ValueError('scrollTrack differs from the reviewed implementation. Manual port required.')
    for element in ('stage', 'now', 'when', 'clock', 'date', 'source', 'plate', 'rows'):
        if len(re.findall(r'\bid=["\']' + element + r'["\']', text)) != 1:
            raise ValueError('Required DOM element differs: ' + element)
    for required in ('function items(kind)', 'state.arranging', 'layout.hidden', 'function applyColours(c)',
                     "var LOOK = $('look').textContent", 'function stageClass()', 'scrollTrack(rowEl, tiles[c], instant)'):
        if required not in text:
            raise ValueError('Unrecognised Home runtime: ' + required)
    matches = list(re.finditer(r'<style\s+id=["\']look["\']\s*>([\s\S]*?)</style>', text))
    if len(matches) != 1:
        raise ValueError('Expected one inline look stylesheet.')
    look = matches[0].group(1)
    for selector in ('#rows{', '#rows:before,#rows:after{', '.track{', '.row.empty{', '.arranging .row.empty{'):
        if selector not in look:
            raise ValueError('Layout stylesheet structure has changed: ' + selector)
    if '#rows' in text[matches[0].end():text.find('</head>')]:
        raise ValueError('Additional head styling targets rows; manual review required.')
    original = text
    css = CSS_START + source('stacked.css') + '\n' + source('clean-weather.css') + CSS_END
    insertion = matches[0].end() - len('</style>')
    text = text[:insertion] + css + text[insertion:]
    text = replace_once(text, old_scroll, SCROLL_START + new_scroll + SCROLL_END)
    text = replace_once(text, '<main id="rows"></main>',
                        CARD_START + source('weather-card.html') + CARD_END + '<main id="rows"></main>')
    text = replace_once(text, '</body>', JS_START + source('weather.js') + JS_END + '</body>')
    if not re.search(r'<meta\s+[^>]*name=["\']referrer["\']', text, re.I):
        text = replace_once(text, '<head>', '<head>' + META)
    if strip_theme(text) != original:
        raise ValueError('Round-trip preservation check failed.')
    return text


def verify(text: str) -> str:
    original = strip_theme(text)
    if add_theme(original) != text:
        raise ValueError('Generated Home page is out of sync with the theme source.')
    return original


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('check', 'build'))
    p.add_argument('input', type=Path)
    p.add_argument('output', nargs='?', type=Path)
    a = p.parse_args()
    try:
        text = a.input.read_bytes().decode('utf-8')
        if a.mode == 'check':
            verify(text)
            print('PASS: generated Home matches source; upstream round-trip is intact.')
        else:
            if a.output is None or a.input.resolve() == a.output.resolve():
                raise ValueError('Supply a distinct output path; do not overwrite the input.')
            if a.output.exists():
                raise ValueError('Output exists; choose a new path.')
            original = strip_theme(text) if TAG in text else text
            a.output.write_bytes(add_theme(original).encode('utf-8'))
            print('Created:', a.output)
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print('STOP:', exc, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
