#!/usr/bin/env python3
"""Independent browser regressions: stock/custom accents and translated weather.
Mocked API and translation responses, not scripts/check-dashboards.js.
"""
import asyncio
import importlib.util
import json
import shutil
from pathlib import Path
from playwright.async_api import async_playwright
from location_browser_test import fixture, weather

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('theme_ci', ROOT/'build.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
STOCK = (ROOT/'tests/fixtures/home-stock.html').read_text()
PATCHED = b.add_theme(STOCK)

async def run():
    checks = []
    def check(name, ok, detail=None):
        if not ok: raise AssertionError(name + ': ' + str(detail))
        checks.append({'test': name, 'result':'PASS'})
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=shutil.which('chromium'), headless=True, args=['--no-sandbox'])
        async def load(html, colours=None, translations=None):
            page = await browser.new_page(viewport={'width':1920, 'height':1080})
            data = fixture(); data['layout']['colours'] = colours
            mock = (ROOT/'tests/mock-browser.js').read_text()
            mock = (mock.replace('__FIXTURE__', json.dumps(data)).replace('__WEATHER__', json.dumps(weather()))
                    .replace('__MODE__', '"normal"').replace('__CACHE__', 'null').replace('__STORAGE_ERROR__', 'false'))
            mock += '\nvar __translations=' + json.dumps(translations or {}) + ';\n'
            mock += r"""
window.t=function(k,f,a){var s=Object.prototype.hasOwnProperty.call(__translations,k)?__translations[k]:(f||k);
return s.replace(/\{([^}]+)\}/g,function(m,n){return a&&a[n]!==undefined?String(a[n]):m;});};
(function(){var es=document.querySelectorAll('[data-t],[data-t-title],[data-t-placeholder],[data-t-aria-label]');
for(var i=0;i<es.length;i++){var e=es[i], k=e.getAttribute('data-t');if(k)e.textContent=t(k,e.textContent);
['title','placeholder','aria-label'].forEach(function(a){var key=e.getAttribute('data-t-'+a);if(key)e.setAttribute(a,t(key,e.getAttribute(a)));});}}());
"""
            errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
            await page.set_content(html.replace('<script src="/assets/i18n.js"></script>', '<script>'+mock+'</script>'))
            await page.wait_for_selector('.tile.focus')
            return page, errors
        async def focus_colour(page):
            return await page.locator('#rows .tile.focus').first.evaluate('(e)=>getComputedStyle(e).outlineColor')
        async def swap_colour(page, colour):
            await page.evaluate("c=>{window.__ghTest.fixture.layout.colours=c;document.dispatchEvent(new Event('webOSRelaunch'));}",colour)
            await page.wait_for_timeout(90)
        # Compare to the *unchanged stock runtime*, not a test-specific colour expectation.
        palettes=[None, {'text':'#ece7df','accent':'#ece7df'}, {'text':'#ffffff','accent':'#e9ad55'},
                  {'text':'#EEEAF8','accent':'#D7B36A'}, {'text':'#d4d4d4','accent':'#1aaaff'},
                  {'text':'#ece7df','accent':'#a39d93'}, {'text':'#ece7df','accent':'#231d12'}]
        stock, se = await load(STOCK)
        patched, pe = await load(PATCHED)
        for i,c in enumerate(palettes):
            await swap_colour(stock,c); await swap_colour(patched,c)
            a,z=await focus_colour(stock),await focus_colour(patched)
            check('Focused dock matches stock palette '+str(i),a==z,{'stock':a,'custom':z})
        await swap_colour(stock,None);await swap_colour(patched,None)
        check('Returning to default restores stock outline', await focus_colour(stock)==await focus_colour(patched))
        check('No JS errors during palette changes',not se and not pe, se+pe)
        check('Known regression default is warm white, not amber',await focus_colour(patched)=='rgb(236, 231, 223)')
        await stock.close();await patched.close()
        mapping={'home.weather.change':'Cambiar','home.weather.locationTitle':'Ubicacion del tiempo',
                 'home.weather.locationExample':'Por ejemplo, Madrid', 'home.weather.closeSettings':'Cerrar ajustes del tiempo',
                 'home.weather.loading':'Cargando el tiempo','home.weather.forLocation':'Tiempo en {location}',
                 'home.weather.currentLocation':'Actual: {location}','home.weather.searchHint':'Escribe una localidad y busca.',
                 'home.weather.partlyCloudy':'Parcialmente nublado','home.weather.feelsLike':'Sensacion de {temperature}',
                 'home.weather.updatedAt':'Actualizado {time}','home.weather.modelTitle':'Tiempo de {location}. Zona: {timezone}.'}
        page, errors = await load(PATCHED, translations=mapping)
        check('Static weather button uses translation',await page.locator('#dnd-wx-change').inner_text()=='Cambiar')
        check('Location name remains un-translated data',await page.locator('#dnd-wx-place').inner_text()=='Staines-upon-Thames')
        check('Loading state uses translated JS',await page.locator('#dnd-wx-condition').inner_text()=='Cargando el tiempo')
        check('Accessible weather name uses parameterised translation',(await page.locator('#dnd-weather').get_attribute('aria-label')).startswith('Tiempo en Staines-upon-Thames'))
        await page.locator('#dnd-wx-change').click()
        check('Dialog title uses translation',await page.locator('#dnd-location-title').inner_text()=='Ubicacion del tiempo')
        check('Input placeholder uses translated attribute',await page.locator('#dnd-location-query').get_attribute('placeholder')=='Por ejemplo, Madrid')
        check('Close aria-label uses translated attribute',await page.locator('#dnd-location-close').get_attribute('aria-label')=='Cerrar ajustes del tiempo')
        check('Search hint uses translated JS',await page.locator('#dnd-location-status').inner_text()=='Escribe una localidad y busca.')
        check('Missing locale keys retain English fallback',await page.locator('#dnd-location-save').inner_text()=='Save location')
        await page.locator('#dnd-location-cancel').click()
        await page.wait_for_timeout(2200)
        check('Live conditions use translation',await page.locator('#dnd-wx-condition').inner_text()=='Parcialmente nublado')
        check('Feels-like text uses parameterised translation',(await page.locator('#dnd-wx-feels').inner_text()).startswith('Sensacion de '))
        check('Updated timestamp uses translation',(await page.locator('#dnd-wx-stamp').inner_text()).startswith('Actualizado '))
        check('Weather tooltip uses parameters',(await page.locator('#dnd-weather').get_attribute('title')).startswith('Tiempo de Staines-upon-Thames. Zona: Europe/London.'))
        check('No JS errors with translations',not errors,errors)
        await page.close();await browser.close()
    out=ROOT/'tests/_test-output';out.mkdir(exist_ok=True)
    (out/'CI-COMPAT-BROWSER-RESULTS.json').write_text(json.dumps({'scope':'Mocked APIs/i18n; stock runtime colour comparison. Not upstream CI.', 'passed':len(checks),'checks':checks},indent=2))
    print(str(len(checks))+' CI-compatibility browser checks passed')

if __name__=='__main__':asyncio.run(run())
