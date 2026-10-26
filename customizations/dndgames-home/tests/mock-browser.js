/* Test-only XMLHttpRequest and storage fixtures. Never installed on the TV. */
window.__ghTest = { calls: [], weatherCalls: [], fixture: __FIXTURE__, response: __WEATHER__,
  mode: __MODE__, cache: __CACHE__, storageError: __STORAGE_ERROR__ };
(function () {
  var t = window.__ghTest, memory = {};
  if (t.cache !== null) memory['dnd.glasshouse.weather.v21.staines'] = JSON.stringify({savedAt:Date.now()-t.cache*60000,payload:t.response});
  Object.defineProperty(window,'localStorage',{configurable:true,value:{
    getItem:function(k){if(t.storageError)throw new Error('blocked');return memory[k]||null;},
    setItem:function(k,v){if(t.storageError)throw new Error('blocked');memory[k]=String(v);}
  }});
  function X() { this.headers={};this.withCredentials=false;this.status=0; }
  X.prototype.open=function(method,url){this.method=method;this.url=url;};
  X.prototype.setRequestHeader=function(k,v){this.headers[k.toLowerCase()]=v;};
  X.prototype.send=function(body){
    var x=this;
    setTimeout(function(){
      var value={ok:true}, status=200, path=x.url.split('?')[0], data=body?JSON.parse(body):null;
      if(x.url.indexOf('https://api.open-meteo.com/')===0){
        t.weatherCalls.push({url:x.url,headers:x.headers,withCredentials:x.withCredentials});
        value=JSON.parse(JSON.stringify(t.response));
        if(t.mode==='offline'){status=503;value={error:true};}
        if(t.mode==='rate-limit'){status=429;value={error:true};}
        if(t.mode==='malformed')value={wrong:'shape'};
        if(t.mode==='wrong-units')value.current_units.temperature_2m='F';
        if(t.mode==='partial'){delete value.daily;value.current.apparent_temperature=null;}
      } else {
        t.calls.push({path:path,body:data});
        if(path==='/api/home/catalogue')value=t.fixture;
        if(path==='/api/home/now')value={kind:'input',port:2,title:'Switch2 Game Console'};
        if(path==='/api/home/picture')value={ok:false};
        if(path==='/api/home/beat')value={ok:true,build:'test',layoutVersion:'test1',wallpapers:t.fixture.wallpapers};
        if(path==='/api/home/layout'){
          if(data){Object.keys(data).forEach(function(k){if(k!=='order')t.fixture.layout[k]=data[k];});
            Object.keys(data.order||{}).forEach(function(k){t.fixture.order[k]=data.order[k];});}
          value={ok:true,layout:t.fixture.layout};
        }
        if(path==='/api/home/recents')value={ok:true,apps:[{id:'youtube.leanback.v4',title:'YouTube'}]};
      }
      x.status=status;x.responseText=JSON.stringify(value);
      if(x.onload)x.onload();
    },20);
  };
  window.XMLHttpRequest=X;
}());
function t(k,f,a){return (f||k).replace(/\{([^}]+)\}/g,function(m,n){return a&&a[n]!==undefined?String(a[n]):m;});}
