#!/usr/bin/env python3
"""Browser tests: mock APIs and localStorage. No live TV/network."""
import asyncio
import importlib.util
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('theme',ROOT/'build.py'); b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
PAGE=b.add_theme((ROOT/'tests/fixtures/home-stock.html').read_text())
OUT=ROOT/'tests/_test-output'; OUT.mkdir(exist_ok=True)
SETTINGS='dnd.glasshouse.weather.settings.v1'
I18N="function t(k,f,a){return(f||k).replace(/\\{([^}]+)\\}/g,function(m,n){return a&&a[n]!==undefined?String(a[n]):m;});}"
EDINBURGH={'name':'Edinburgh','admin1':'Scotland','country':'United Kingdom','country_code':'GB','latitude':55.95206,'longitude':-3.19648,'timezone':'Europe/London'}
PARIS={'name':'Paris','admin1':'Ile-de-France','country':'France','country_code':'FR','latitude':48.85341,'longitude':2.3488,'timezone':'Europe/Paris'}
def weather():
    d=datetime.now(timezone.utc).replace(second=0,microsecond=0)
    return {'utc_offset_seconds':0,'current_units':{'temperature_2m':'\u00b0C','wind_speed_10m':'mp/h'},
            'current':{'time':d.strftime('%Y-%m-%dT%H:%M'),'temperature_2m':14.5,'apparent_temperature':13.1,'weather_code':2,'is_day':1,'wind_speed_10m':7.4},
            'daily':{'time':[(d+timedelta(days=i)).strftime('%Y-%m-%d') for i in range(4)],'weather_code':[2,3,61,0],
                     'temperature_2m_max':[16,15,14,17],'temperature_2m_min':[10,9,8,11]}}
def fixture():
    visible=['apps','youtube','spotify','media','glasshouse','lg-home']; hidden=['hidden-'+str(i) for i in range(11)]
    ids=visible[:-1]+hidden+['lg-home']
    return {'ok':True,'apps':[{'id':i,'title':{'apps':'Apps','youtube':'YouTube','spotify':'Spotify','media':'Media','glasshouse':'Glasshouse'}.get(i,i)} for i in ids if i!='lg-home'],
      'devices':[{'id':'hdmi1','port':1,'name':'HDMI 1','unused':True},{'id':'hdmi2','port':2,'name':'Nintendo Switch','unused':False},{'id':'hdmi3','port':3,'name':'HDMI 3','unused':True}],
      'channels':[],'sources':{'channels':0},'order':{'app':ids,'dev':['hdmi1','hdmi2','hdmi3'],'ch':[]},
      'layout':{'rows':['dev','app','ch'],'sort':{'app':'custom','dev':'custom','ch':'custom'},'hidden':{'app':hidden,'dev':[],'ch':[]},'channels':[],'hintSeen':True,'picture':False,'colours':{'text':'#EEEAF8','accent':'#D7B36A'}},
      'layoutVersion':'fixture1','wallpapers':{'available':False}}

async def run():
    checks=[]
    def check(name,ok,detail=None):
        if not ok: raise AssertionError(name+': '+str(detail))
        checks.append({'test':name,'result':'PASS'})
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
        async def scenario(storage=None,broken_storage=False,geocode_mode='normal',forecast_mode='normal',size=None):
            ctx=await browser.new_context(viewport=size or {'width':1920,'height':1080})
            state={'calls':[],'forecast':[],'search':[],'data':fixture(),'errors':[],'mode':geocode_mode,'forecast_mode':forecast_mode}
            async def route(r):
                url=urlparse(r.request.url);path=url.path;q=parse_qs(url.query)
                if url.netloc=='geocoding-api.open-meteo.com':
                    state['search'].append({'url':r.request.url,'headers':r.request.headers})
                    query=q.get('name',[''])[0]
                    if query=='Slow': await asyncio.sleep(.8)
                    if state['mode']=='offline': return await r.abort()
                    if state['mode']=='rate': return await r.fulfill(status=429,json={'error':True})
                    if state['mode']=='malformed': return await r.fulfill(status=200,body='not JSON')
                    if state['mode']=='empty': results=[]
                    elif state['mode']=='many': results=[dict(EDINBURGH,name='Location '+str(i)) for i in range(8)]
                    elif state['mode']=='malicious': results=[dict(EDINBURGH,name='<img src=x onerror=alert(1)>')]
                    elif state['mode']=='invalid': results=[dict(EDINBURGH,latitude=100),dict(EDINBURGH,timezone='../../etc'),dict(EDINBURGH,longitude='-3')]
                    elif query=='Slow': results=[dict(PARIS,name='Slow City')]
                    elif 'Paris' in query: results=[PARIS,dict(PARIS,admin1='Texas',country='United States',country_code='US',latitude=33.66,longitude=-95.55,timezone='America/Chicago')]
                    else: results=[EDINBURGH,dict(EDINBURGH,admin1='Indiana',country='United States',country_code='US',latitude=39.35,longitude=-85.97,timezone='America/Indiana/Indianapolis')]
                    try:return await r.fulfill(json={'results':results})
                    except Exception:return
                if url.netloc=='api.open-meteo.com':
                    state['forecast'].append({'url':r.request.url,'query':q,'headers':r.request.headers})
                    if state['forecast_mode']=='delayed' and q.get('latitude')==['51.434']: await asyncio.sleep(2)
                    if state['forecast_mode']=='offline': return await r.abort()
                    try:return await r.fulfill(json=weather())
                    except Exception:return
                if path=='/home': return await r.fulfill(content_type='text/html',body=PAGE)
                if path=='/assets/i18n.js': return await r.fulfill(content_type='application/javascript',body=I18N)
                if path.startswith('/assets/'):return await r.fulfill(status=404,body='')
                if path.startswith('/api/home/'):
                    body=r.request.post_data_json if r.request.method=='POST' else None
                    state['calls'].append((path,body))
                    value={'ok':True}
                    if path.endswith('/catalogue'):value=state['data']
                    if path.endswith('/now'):value={'kind':'app','title':'Glasshouse'}
                    if path.endswith('/beat'):value={'ok':True,'build':'test','layoutVersion':'fixture1','wallpapers':{'available':False}}
                    if path.endswith('/layout'):
                        state['data']['layout'].update({k:v for k,v in (body or {}).items() if k!='order'})
                        state['data']['order'].update((body or {}).get('order',{}));value={'ok':True,'layout':state['data']['layout']}
                    if path.endswith('/recents'):value={'ok':True,'apps':[{'id':'youtube','title':'YouTube'}]}
                    return await r.fulfill(json=value)
                return await r.fulfill(status=404,body='')
            page=await ctx.new_page();page.on('pageerror',lambda e:state['errors'].append(str(e)))
            async def respond(url, method, body, headers, credentials):
                from types import SimpleNamespace
                class MockRoute:
                    request=SimpleNamespace(url=url,method=method,post_data_json=json.loads(body) if body else None,headers=headers)
                    async def fulfill(self,status=200,json=None,body='',content_type=''):
                        import json as j
                        return {'status':status,'body':j.dumps(json) if json is not None else body}
                    async def abort(self):return {'status':0,'error':True}
                return await route(MockRoute())
            await page.expose_function('__respond',respond)
            mock=r"""
(function(){
var store=__STORAGE__,broken=__BROKEN__;
window.__store=store;
var ls={};
Object.defineProperties(ls,{
getItem:{value:function(k){return Object.prototype.hasOwnProperty.call(store,k)?store[k]:null;}},
setItem:{value:function(k,v){if(broken)throw new Error('Storage denied');store[k]=String(v);if(!Object.prototype.hasOwnProperty.call(ls,k))Object.defineProperty(ls,k,{enumerable:true,configurable:true,get:function(){return store[k];}});}},
removeItem:{value:function(k){delete store[k];delete ls[k];}},
clear:{value:function(){Object.keys(store).forEach(function(k){delete store[k];delete ls[k];});}}
});
Object.keys(store).forEach(function(k){Object.defineProperty(ls,k,{enumerable:true,configurable:true,get:function(){return store[k];}});});
Object.defineProperty(window,'localStorage',{configurable:true,value:ls});
function X(){this.headers={};this.withCredentials=false;this.aborted=false;}
X.prototype.open=function(m,u){this.method=m;this.url=u;};
X.prototype.setRequestHeader=function(k,v){this.headers[k.toLowerCase()]=v;};
X.prototype.abort=function(){this.aborted=true;if(this.onabort)this.onabort();};
X.prototype.send=function(body){var x=this;window.__respond(x.url,x.method,body,x.headers,x.withCredentials).then(function(r){
if(x.aborted)return;
if(!r||r.error){if(x.onerror)x.onerror();return;}
x.status=r.status;x.responseText=r.body;if(x.onload)x.onload();
}).catch(function(){if(!x.aborted&&x.onerror)x.onerror();});};
window.XMLHttpRequest=X;
}());
"""
            async def render_page(store):
                injection=mock.replace('__STORAGE__',json.dumps(store)).replace('__BROKEN__',json.dumps(broken_storage)) + I18N
                html=PAGE.replace('<script src="/assets/i18n.js"></script>','<script>'+injection+'</script>')
                await page.set_content(html,wait_until='load');await page.wait_for_selector('.tile.app')
            await render_page({SETTINGS:storage} if storage is not None else {})
            async def reload_mock():
                store=await page.evaluate('window.__store')
                # New document/window to model reload, same mocked persistent store.
                await page.goto('about:blank')
                await render_page(store)
            state['reload']=reload_mock
            return ctx,page,state
        async def key(page,code):
            await page.evaluate("c=>{document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:c,which:c,bubbles:true}));document.dispatchEvent(new KeyboardEvent('keyup',{keyCode:c,which:c,bubbles:true}));}",code)
        async def search(page,term):
            await page.locator('#dnd-location-query').fill(term)
            await page.locator('#dnd-location-search').click()
            await page.wait_for_function("document.getElementById('dnd-location-results').getAttribute('aria-busy')==='false'")
        ctx,page,s=await scenario(); await page.wait_for_timeout(2200)
        check('Initial Staines forecast retained',await page.locator('#dnd-wx-place').inner_text()=='Staines-upon-Thames' and len(s['forecast'])==1)
        check('No geocoding until explicit search',not s['search'])
        check('Six visible apps retained',await page.locator('.tile.app').count()==6)
        check('Headings hidden normally',await page.locator('#rows h2').evaluate_all('(es)=>es.every(e=>getComputedStyle(e).display==="none")'))
        wb=await page.locator('#dnd-weather').bounding_box(); cb=await page.locator('#when').bounding_box(); ab=await page.locator('[data-key="app"] .track').bounding_box()
        check('Weather left / clock right / bottom dock unchanged',abs(wb['x']-90)<1 and abs(cb['x']+cb['width']-1830)<1 and ab['y']>820)
        await page.keyboard.press('ArrowUp')
        check('Up above first row focuses Change',await page.locator('#dnd-wx-change').evaluate('(e)=>document.activeElement===e'))
        await page.keyboard.press('Enter')
        check('Remote OK opens location dialog',await page.locator('#dnd-weather-settings').is_visible())
        check('Open dialog does not launch an application',not any(x=='/api/home/open' for x,y in s['calls']))
        await search(page,'Edinburgh')
        check('Search returns region and country choices',await page.locator('.dnd-location-result').count()==2 and 'Scotland, United Kingdom' in await page.locator('#dnd-location-results').inner_text())
        check('Search alone does not change location',await page.locator('#dnd-wx-place').inner_text()=='Staines-upon-Thames')
        await page.locator('.dnd-location-result').first.click()
        check('Result selection requires explicit Save',await page.locator('#dnd-wx-place').inner_text()=='Staines-upon-Thames' and await page.locator('#dnd-location-save').is_enabled())
        await page.locator('#dnd-location-cancel').click()
        check('Cancel preserves previous location and no settings write',await page.evaluate('localStorage.getItem('+json.dumps(SETTINGS)+')') is None)
        await key(page,406)
        check('Blue button shortcut opens settings',await page.locator('#dnd-weather-settings').is_visible())
        await search(page,'Paris')
        await page.locator('.dnd-location-result').first.click()
        await page.locator('#dnd-location-save').click()
        await page.wait_for_timeout(300)
        record=await page.evaluate('JSON.parse(localStorage.getItem('+json.dumps(SETTINGS)+'))')
        check('Save persists selected town coordinates timezone',record['location']['latitude']==48.85341 and record['location']['timezone']=='Europe/Paris')
        check('Forecast uses selected location not fixed Staines',s['forecast'][-1]['query']['latitude']==['48.85341'] and s['forecast'][-1]['query']['timezone']==['Europe/Paris'])
        check('Card title and country update',await page.locator('#dnd-wx-place').inner_text()=='Paris' and await page.locator('#dnd-wx-country').inner_text()=='FR')
        check('Old-location cache removed',not await page.evaluate("Object.keys(localStorage).some(k=>k.indexOf('weather.v23.51.434|')!==-1)"))
        check('No backend settings altered by search or save',not any(x=='/api/home/layout' for x,y in s['calls']))
        check('No authentication headers added to provider requests',all('authorization' not in c['headers'] and 'cookie' not in c['headers'] and 'referer' not in c['headers'] for c in s['search']+s['forecast']))
        await s['reload'](); await page.wait_for_selector('.tile.app')
        check('Selection survives document reload with retained mock storage',await page.locator('#dnd-wx-place').inner_text()=='Paris')
        await page.locator('#dnd-wx-change').click();await search(page,'Edinburgh')
        # Capture an actual rendered implementation preview, using simulated data.
        await page.add_style_tag(content="#stage{background:linear-gradient(135deg,#101624,#1c142b)}")
        await page.evaluate("var e=document.createElement('div');e.style.cssText='position:fixed;bottom:8px;left:20px;color:white;font:14px sans-serif;z-index:99';e.textContent='IMPLEMENTATION PREVIEW - SIMULATED WEATHER AND APPS';document.body.appendChild(e);")
        await page.screenshot(path=str(OUT/'location-selector-example.png'))
        await page.locator('#dnd-location-cancel').click()
        await key(page,461);await key(page,40) # leave weather focus, then move Inputs -> Apps
        await page.keyboard.press('ArrowRight');await page.keyboard.press('Enter'); await page.wait_for_timeout(100)
        check('Normal app launching still works',any(x=='/api/home/open' and y.get('kind')=='app' for x,y in s['calls']))
        await page.keyboard.down('Enter');await page.wait_for_timeout(850);await page.keyboard.up('Enter')
        check('Long OK Arrange retained', 'arranging' in (await page.locator('#stage').get_attribute('class') or ''))
        check('Hidden apps only reveal in Arrange',await page.locator('.tile.hidden').count()==11)
        await key(page,406)
        check('Weather shortcut does not hijack Arrange',not await page.locator('#dnd-weather-settings').is_visible())
        await key(page,461);await page.wait_for_timeout(100)
        check('Hidden selections preserved after Arrange',await page.locator('.tile.app').count()==6)
        await key(page,461);await page.wait_for_timeout(100)
        check('Recent apps panel retained','recents' in (await page.locator('#stage').get_attribute('class') or ''))
        check('No browser errors across normal navigation/search/save',not s['errors'],s['errors'])
        await ctx.close()
        # Failure cases keep the current location and core navigation operational.
        for mode,expected in [('offline','unavailable'),('rate','limited'),('malformed','unavailable'),('empty','No matching'),('invalid','No matching')]:
            ctx,page,s=await scenario(geocode_mode=mode)
            await page.locator('#dnd-wx-change').click();await search(page,'Edinburgh')
            check(mode+' search explains failure',expected in await page.locator('#dnd-location-status').inner_text())
            check(mode+' search preserves location',await page.locator('#dnd-wx-place').inner_text()=='Staines-upon-Thames' and await page.locator('#dnd-location-save').is_disabled())
            if mode=='rate':
                await search(page,'Paris');check('Rate-limit backoff avoids repeated request',len(s['search'])==1)
            await ctx.close()
        ctx,page,s=await scenario(broken_storage=True)
        await page.locator('#dnd-wx-change').click();await search(page,'Edinburgh');await page.locator('.dnd-location-result').first.click();await page.locator('#dnd-location-save').click()
        check('Storage failure is not falsely reported as saved','cannot save' in await page.locator('#dnd-location-status').inner_text() and await page.locator('#dnd-wx-place').inner_text()=='Staines-upon-Thames')
        await ctx.close()
        for bad in ['not json',json.dumps({'version':1,'location':{'name':'bad'}}),json.dumps({'version':99,'location':{}})]:
            ctx,page,s=await scenario(storage=bad)
            check('Invalid stored setting falls back without breaking Home',await page.locator('#dnd-wx-place').inner_text()=='Staines-upon-Thames' and await page.locator('.tile.app').count()==6)
            await ctx.close()
        ctx,page,s=await scenario(geocode_mode='malicious')
        await page.locator('#dnd-wx-change').click();await search(page,'XSS')
        check('Provider labels are rendered as text, not HTML',await page.locator('#dnd-location-results img').count()==0 and '<img' in await page.locator('#dnd-location-results').inner_text())
        await ctx.close()
        ctx,page,s=await scenario()
        await page.locator('#dnd-wx-change').click();await page.locator('#dnd-location-query').fill('Slow');await page.locator('#dnd-location-search').click()
        await page.locator('#dnd-location-query').fill('Paris');await page.locator('#dnd-location-search').click();await page.wait_for_timeout(1000)
        check('Late old search cannot replace latest results','Slow City' not in await page.locator('#dnd-location-results').inner_text() and 'Paris' in await page.locator('#dnd-location-results').inner_text())
        await page.locator('#dnd-location-cancel').click();await ctx.close()
        ctx,page,s=await scenario(forecast_mode='delayed')
        await page.wait_for_timeout(2100) # old forecast is now in flight
        await page.locator('#dnd-wx-change').click();await search(page,'Edinburgh');await page.locator('.dnd-location-result').first.click();await page.locator('#dnd-location-save').click()
        await page.wait_for_timeout(2300)
        check('Late old forecast cannot overwrite selected city',await page.locator('#dnd-wx-place').inner_text()=='Edinburgh' and not await page.evaluate("Object.keys(localStorage).some(k=>k.indexOf('weather.v23.51.434|')!==-1)"))
        await ctx.close()
        ctx,page,s=await scenario(geocode_mode='many')
        await page.locator('#dnd-wx-change').click();await search(page,'Location')
        for i in range(7):await page.keyboard.press('ArrowDown')
        focused=await page.evaluate('document.activeElement.getAttribute("data-result")')
        scroll=await page.locator('#dnd-location-results').evaluate('(e)=>e.scrollTop')
        check('Remote can scroll through eight location results',focused=='7' and scroll>0)
        await page.keyboard.press('Enter');await page.keyboard.press('Enter');await page.wait_for_timeout(200)
        check('Remote OK selects and saves without launching an app',await page.locator('#dnd-wx-place').inner_text()=='Location 7' and not any(x=='/api/home/open' for x,y in s['calls']))
        await ctx.close()
        ctx,page,s=await scenario(forecast_mode='offline')
        await page.wait_for_timeout(2300)
        check('Offline forecast keeps core Home and location control available',await page.locator('#dnd-weather').get_attribute('data-weather-state')=='unavailable' and await page.locator('.tile.app').count()==6 and await page.locator('#dnd-wx-change').is_visible())
        await ctx.close()
        ctx,page,s=await scenario(size={'width':3840,'height':2160})
        await page.locator('#dnd-wx-change').click()
        rect=await page.locator('.dnd-location-panel').bounding_box()
        check('4K scaling keeps dialog within screen',rect['x']>=0 and rect['y']>=0 and rect['x']+rect['width']<=3840 and rect['y']+rect['height']<=2160)
        await ctx.close();await browser.close()
    (OUT/'LOCATION-BROWSER-RESULTS.json').write_text(json.dumps({'environment':'Headless Chromium with mocked APIs and storage; not tested on physical LG TV','checks':checks,'passed':len(checks)},indent=2))
    print(str(len(checks))+' browser checks passed')
if __name__=='__main__': asyncio.run(run())
