#!/usr/bin/env python3
"""Regression tests using MOCK APIs. No TV or live forecast is contacted."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import os
from pathlib import Path
import re
from urllib.parse import urlparse
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
import build as theme_build
PAGE_PATH = Path(os.environ.get('GH_HOME_PAGE', str(ROOT.parents[1]/'server/assets/home.html')))
PAGE = PAGE_PATH.read_text() if PAGE_PATH.exists() else theme_build.add_theme((ROOT/'tests/fixtures/home-stock.html').read_text())
OUT = ROOT / 'tests' / '_test-output'
OUT.mkdir(exist_ok=True)
BG = Path(os.environ.get('GH_PREVIEW_IMAGE', str(ROOT/'tests/optional-wallpaper.jpg')))
BASE = ROOT/'tests/fixtures/home-stock.html'
VISIBLE = ['com.webos.app.apps', 'youtube.leanback.v4', 'spotify', 'com.webos.app.photovideo', 'glasshouse', 'lg-home']
HIDDEN = ['hidden-' + str(i) for i in range(11)]
IDS = VISIBLE[:-1] + HIDDEN + ['lg-home']
TITLES = ['Apps', 'YouTube', 'Spotify', 'Media Player', 'Glasshouse']
COLOURS = ['#31384a', '#d93c3c', '#166a38', '#394b61', '#635677']
I18N = "function t(k,f,a){var s=f||k;return s.replace(/\\{([^}]+)\\}/g,function(m,n){return a&&a[n]!==undefined?String(a[n]):m;});}"


def payload():
    dt = datetime.now(ZoneInfo('Europe/London')).replace(second=0, microsecond=0)
    return {'utc_offset_seconds':int(dt.utcoffset().total_seconds()),
            'current_units':{'temperature_2m':'\u00b0C','wind_speed_10m':'mp/h'},
            'current':{'time':dt.strftime('%Y-%m-%dT%H:%M'),'temperature_2m':14.5,
                       'apparent_temperature':13.2,'weather_code':2,'is_day':1,'wind_speed_10m':7.4},
            'daily':{'time':[(dt+timedelta(days=i)).strftime('%Y-%m-%d') for i in range(4)],
                     'weather_code':[2,3,61,0],'temperature_2m_max':[16,15,14,16],'temperature_2m_min':[10,9,8,9]}}


def fixture():
    return {'ok':True,'apps':[{'id':a,'title':TITLES[i] if i<5 else 'Hidden app '+str(i),
                             'icon':'/mock-icon/'+str(i)} for i,a in enumerate(IDS) if a!='lg-home'],
            'devices':[{'id':'hdmi1','port':1,'name':'HDMI 1','unused':True},
                       {'id':'hdmi2','port':2,'name':'Switch2 Game Console','unused':False},
                       {'id':'hdmi3','port':3,'name':'HDMI 3','unused':True}],
            'channels':[],'sources':{'channels':0},'order':{'app':IDS[:],'dev':['hdmi1','hdmi2','hdmi3'],'ch':[]},
            'layout':{'rows':['dev','app','ch'],'sort':{'app':'custom','dev':'custom','ch':'custom'},
                      'hidden':{'app':HIDDEN[:],'dev':[],'ch':[]},'channels':[],'hintSeen':True,
                      'picture':False,'colours':{'text':'#EEEAF8','accent':'#B9A6FF'}},
            'layoutVersion':'test1','wallpapers':{'available':True,'slots':{'morning':True,'afternoon':True,'evening':True,'night':True},'revision':'test'}}


async def run():
    results=[]
    def check(name, condition, detail=''):
        if not condition: raise AssertionError(name+': '+str(detail))
        results.append({'test':name,'result':'PASS','detail':detail})
    check('Generated Home source matches theme and round-trips', bool(theme_build.verify(PAGE)))
    async with async_playwright() as p:
        import shutil
        binary = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('chromium-browser')
        browser=await p.chromium.launch(**({'executable_path':binary} if binary else {}),headless=True,args=['--no-sandbox'])
        async def scenario(name,mode='success',cache=None,storage_error=False,viewport=None):
            import base64
            ctx=await browser.new_context(viewport=viewport or {'width':1920,'height':1080},device_scale_factor=1)
            data=fixture();response=payload();errors=[]
            for i,app in enumerate(data['apps']):
                title=TITLES[i] if i<5 else 'H'
                svg='<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" rx="18" fill="'+COLOURS[i%len(COLOURS)]+'"/><text x="50" y="56" fill="white" text-anchor="middle" font-family="sans-serif" font-size="12">'+title+'</text></svg>'
                app['icon']='data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()
            mock=(ROOT/'tests/mock-browser.js').read_text()
            for key,value in [('__FIXTURE__',data),('__WEATHER__',response),('__MODE__',mode),('__CACHE__',cache),('__STORAGE_ERROR__',storage_error)]:
                mock=mock.replace(key,json.dumps(value))
            test_html=PAGE.replace('<script src="/assets/i18n.js"></script>','<script>'+mock+'</script>')
            page=await ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            await page.set_content(test_html,wait_until='load')
            if BG.exists():
                bg64=base64.b64encode(BG.read_bytes()).decode()
                await page.add_style_tag(content='#wall .layer:first-child{background-image:url(data:image/png;base64,'+bg64+');opacity:.72!important;animation:none!important}')
            await page.wait_for_timeout(2500)
            snapshot=await page.evaluate('window.__ghTest')
            calls=[(r['path'],r['body']) for r in snapshot['calls']]
            return ctx,page,calls,errors,snapshot['weatherCalls'],snapshot['fixture']
        ctx,page,calls,errors,wxcalls,data=await scenario('normal')
        check('Weather success display',await page.get_attribute('#dnd-weather','data-weather-state')=='ready')
        check('Correct town',await page.locator('.wx-place').text_content()=='Staines-upon-Thames')
        check('Celsius and mph',await page.locator('#dnd-wx-temp').text_content()=='15\u00b0C' and 'mph' in await page.locator('#dnd-wx-detail').text_content())
        check('Three upcoming forecast days',await page.locator('.wx-day').count()==3)
        check('Normal mode headings hidden',await page.locator('#rows .row > h2').evaluate_all('(els)=>els.every(e=>getComputedStyle(e).display==="none")'))
        check('Six visible apps retained',await page.locator('#rows [data-key="app"] .tile').count()==6)
        check('No hidden app in normal mode',await page.locator('#rows .tile.hidden').count()==0)
        check('No configuration writes on load',not any(u=='/api/home/layout' for u,b in calls))
        box=await page.locator('#dnd-weather').bounding_box()
        check('Weather aligned top left',abs(box['x']-90)<2 and abs(box['y']-52)<2,box)
        clock=await page.locator('#when').bounding_box()
        check('Clock aligned top right',abs(clock['x']+clock['width']-1830)<2 and abs(clock['y']-52)<2,clock)
        check('Clock text right aligned',await page.locator('#when').evaluate('(e)=>getComputedStyle(e).textAlign')=='right')
        check('Clock/weather do not overlap',box['x']+box['width']<clock['x'])
        box=await page.locator('[data-key="app"] .track').bounding_box()
        check('App dock remains near bottom',box['y']>820 and box['y']+box['height']<1080,box)
        check('No third-party credentials',len(wxcalls)==1 and 'authorization' not in wxcalls[0]['headers'] and not wxcalls[0]['withCredentials'] and 'name="referrer" content="no-referrer"' in PAGE)
        await page.evaluate("var p=document.createElement('div');p.id='preview-label';p.textContent='LAYOUT PREVIEW - EXAMPLE WEATHER, NOT LIVE';p.style.cssText='position:fixed;bottom:8px;left:16px;z-index:99;font:12px sans-serif;color:white;opacity:.7';document.body.appendChild(p);")
        await page.screenshot(path=str(OUT/'PREVIEW-v2.2-EXAMPLE.png'))
        await page.locator('#preview-label').evaluate('(e)=>e.remove()')
        await page.keyboard.press('ArrowDown')
        check('Down navigates Inputs to Apps',await page.locator('.row.active').get_attribute('data-key')=='app')
        await page.keyboard.press('ArrowRight');await page.keyboard.press('Enter')
        await page.wait_for_timeout(80)
        check('App launch endpoint unchanged',await page.evaluate("window.__ghTest.calls.some(c=>c.path==='/api/home/open'&&c.body.kind==='app'&&c.body.id==='youtube.leanback.v4')"))
        await page.keyboard.down('Enter');await page.wait_for_timeout(900);await page.keyboard.up('Enter')
        check('Long OK enters Arrange','arranging' in (await page.locator('#stage').get_attribute('class') or ''))
        check('Sort headings restored in Arrange',await page.locator('#rows .row > h2').evaluate_all('(els)=>els.every(e=>getComputedStyle(e).display==="block")'))
        check('Original hidden tiles available in Arrange',await page.locator('#rows .tile.hidden').count()==11)
        await page.screenshot(path=str(OUT/'arrange-example.png'))
        await page.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:461,which:461,bubbles:true}));document.dispatchEvent(new KeyboardEvent('keyup',{keyCode:461,which:461,bubbles:true}));")
        await page.wait_for_timeout(150)
        check('Hidden selections preserved after Arrange',await page.evaluate('window.__ghTest.fixture.layout.hidden.app')==HIDDEN and await page.locator('#rows .tile.hidden').count()==0)
        await page.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:461,which:461,bubbles:true}));document.dispatchEvent(new KeyboardEvent('keyup',{keyCode:461,which:461,bubbles:true}));")
        await page.wait_for_timeout(100)
        check('Recent-apps panel still opens','recents' in (await page.locator('#stage').get_attribute('class') or ''))
        check('No JavaScript errors in normal and Arrange',not errors,errors)
        await ctx.close()
        for name,mode,cache,state in [('Offline','offline',None,'unavailable'),('Malformed','malformed',None,'unavailable'),('Wrong units','wrong-units',None,'unavailable'),('Rate limit','rate-limit',None,'unavailable'),('Fresh cache','success',5,'ready'),('Cached offline','offline',20,'cached'),('Expired cache','offline',150,'unavailable'),('Missing optional values','partial',None,'ready')]:
            ctx,page,calls,errors,wxcalls,data=await scenario(name,mode,cache)
            check(name+' state',await page.get_attribute('#dnd-weather','data-weather-state')==state)
            check(name+' does not block Home',await page.locator('[data-key="app"] .tile').count()==6 and not errors,errors)
            if name=='Fresh cache':check('Fresh cache suppresses duplicate weather requests',len(wxcalls)==0)
            if name=='Rate limit':
                await page.clock.install();await page.clock.fast_forward(60000)
                check('429 does not cause immediate retry',await page.evaluate('window.__ghTest.weatherCalls.length')==1)
            if name=='Offline':await page.screenshot(path=str(OUT/'offline-example.png'))
            await ctx.close()
        ctx,page,calls,errors,wxcalls,data=await scenario('Storage blocked',storage_error=True,viewport={'width':3840,'height':2160})
        check('Storage failure does not block weather',await page.get_attribute('#dnd-weather','data-weather-state')=='ready' and not errors,errors)
        box=await page.locator('#dnd-weather').bounding_box()
        check('Correct stage scaling at 4K',abs(box['x']-180)<3 and abs(box['y']-104)<2,box)
        await ctx.close();await browser.close()
    report={'method':'Local Chromium rendering with in-page mock XMLHttpRequest APIs; no live TV, public endpoint, TLS or production CORS test.','checks':len(results),'results':results}
    (OUT/'TEST-RESULTS.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'passed':len(results),'method':report['method']},indent=2))

if __name__=='__main__':asyncio.run(run())
