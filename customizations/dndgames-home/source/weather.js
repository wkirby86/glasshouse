/* DNDGAMES-CLEAN-WEATHER-V21 SCRIPT
 * Independent ES5 widget. No Glasshouse API, remote-key, layout, or root changes.
 * Town-centre coordinates, NOT the user's address. Direct HTTPS, no API key,
 * no credentials or third-party executable code. Model-based weather data.
 */
(function () {
  'use strict';
  if (window.__dndWeatherV21Started) return;
  window.__dndWeatherV21Started = true;
  var card = document.getElementById('dnd-weather');
  if (!card) return;
  var REFRESH_MS = 15 * 60 * 1000, MAX_AGE_MS = 2 * 60 * 60 * 1000;
  var RETRY_MS = 5 * 60 * 1000, TIMEOUT_MS = 10000;
  var CACHE_KEY = 'dnd.glasshouse.weather.v21.staines';
  var URL = 'https://api.open-meteo.com/v1/forecast?latitude=51.434&longitude=-0.5114' +
    '&current=temperature_2m,apparent_temperature,is_day,weather_code,wind_speed_10m' +
    '&daily=weather_code,temperature_2m_max,temperature_2m_min' +
    '&temperature_unit=celsius&wind_speed_unit=mph&timezone=Europe%2FLondon&forecast_days=4';
  var saved = null, nextDue = 0, busy = false, failed = false, timer = null;
  function el(id) { return document.getElementById('dnd-wx-' + id); }
  function text(id, value) { var e = el(id); if (e) e.textContent = value; }
  function numeric(n) { return typeof n === 'number' && isFinite(n); }
  function degrees(n) { return numeric(n) ? String(Math.round(n)) + '\u00b0' : '\u2014'; }
  function clockStamp(r) { return r.current.time.slice(11, 16); }
  function modelTime(r) {
    var m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(r.current.time);
    if (!m || !numeric(r.utc_offset_seconds)) return NaN;
    return Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]) - r.utc_offset_seconds * 1000;
  }
  function valid(r) {
    return !!(r && !r.error && r.current && numeric(r.current.temperature_2m) &&
      typeof r.current.time === 'string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d/.test(r.current.time) &&
      r.current_units && r.current_units.temperature_2m === '\u00b0C' && numeric(modelTime(r)));
  }
  function usable(record) {
    if (!record || !valid(record.payload) || !numeric(record.savedAt)) return false;
    var age = Date.now() - record.savedAt, observedAge = Date.now() - modelTime(record.payload);
    return age >= 0 && age <= MAX_AGE_MS && observedAge >= -60 * 60 * 1000 && observedAge <= MAX_AGE_MS;
  }
  function weather(code, day) {
    switch (code) {
      case 0: return [day === 0 ? 'Clear night' : 'Clear skies', day === 0 ? 'moon' : 'sun'];
      case 1: return ['Mainly clear', day === 0 ? 'moon' : 'sun'];
      case 2: return ['Partly cloudy', 'partly'];
      case 3: return ['Overcast', 'cloud'];
      case 45: case 48: return ['Fog', 'fog'];
      case 51: case 53: case 55: return ['Drizzle', 'rain'];
      case 56: case 57: return ['Freezing drizzle', 'rain'];
      case 61: case 63: case 65: return ['Rain', 'rain'];
      case 66: case 67: return ['Freezing rain', 'rain'];
      case 71: case 73: case 75: case 77: return ['Snow', 'snow'];
      case 80: case 81: case 82: return ['Rain showers', 'rain'];
      case 85: case 86: return ['Snow showers', 'snow'];
      case 95: case 96: case 99: return ['Thunderstorms', 'storm'];
      default: return ['Weather', 'cloud'];
    }
  }
  function icon(kind) {
    var sun = '<circle cx="32" cy="30" r="11"/><path d="M32 9v5m0 32v5M11 30h5m32 0h5M17 15l4 4m22 22l4 4M17 45l4-4m22-22l4-4"/>';
    var cloud = '<path d="M18 43h29a10 10 0 0 0 0-20 15 15 0 0 0-28-3A12 12 0 0 0 18 43z"/>';
    var p = cloud;
    if (kind === 'sun') p = sun;
    if (kind === 'moon') p = '<path d="M44 12a22 22 0 1 0 8 36A24 24 0 0 1 44 12z"/>';
    if (kind === 'partly') p = '<g transform="translate(-3,-9) scale(.8)">' + sun + '</g>' + cloud;
    if (kind === 'rain') p += '<path d="M21 49l-3 7m15-7l-3 7m15-7l-3 7"/>';
    if (kind === 'snow') p += '<path d="M22 49v8m-4-4h8m16-4v8m-4-4h8"/>';
    if (kind === 'storm') p += '<path d="M34 43l-7 10h8l-5 9"/>';
    if (kind === 'fog') p += '<path d="M14 50h36M19 57h25"/>';
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + p + '</svg>';
  }
  function dayName(s) {
    var m = /^(\d{4})-(\d\d)-(\d\d)$/.exec(s || '');
    return m ? ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][new Date(+m[1], +m[2]-1, +m[3], 12).getDay()] : '\u2014';
  }
  function add(parent, cls, value) {
    var e = document.createElement('span'); e.className = cls;
    if (value !== undefined) e.textContent = value;
    parent.appendChild(e); return e;
  }
  function render() {
    if (!usable(saved)) { unavailable(); return; }
    var r = saved.payload, c = r.current, daily = r.daily || {};
    var report = weather(c.weather_code, c.is_day);
    var cached = failed || Date.now() - saved.savedAt >= REFRESH_MS;
    card.setAttribute('data-weather-state', cached ? 'cached' : 'ready');
    text('temp', degrees(c.temperature_2m) + 'C');
    text('condition', report[0]); el('icon').innerHTML = icon(report[1]);
    text('feels', numeric(c.apparent_temperature) ? 'Feels like ' + degrees(c.apparent_temperature) : 'Model-based conditions');
    var detail = [];
    if (daily.temperature_2m_max && daily.temperature_2m_min && daily.time && daily.time[0] === c.time.slice(0,10)) {
      detail.push('H ' + degrees(daily.temperature_2m_max[0]) + '  L ' + degrees(daily.temperature_2m_min[0]));
    }
    if (numeric(c.wind_speed_10m) && r.current_units.wind_speed_10m === 'mp/h') detail.push('Wind ' + Math.round(c.wind_speed_10m) + ' mph');
    // Some API versions use 'mph' instead of 'mp/h'.
    if (numeric(c.wind_speed_10m) && r.current_units.wind_speed_10m === 'mph') detail.push('Wind ' + Math.round(c.wind_speed_10m) + ' mph');
    text('detail', detail.join('  \u00b7  '));
    var days = el('days'); days.innerHTML = '';
    if (daily.time && daily.weather_code && daily.temperature_2m_max && daily.temperature_2m_min) {
      for (var i = 1; i < Math.min(4, daily.time.length); i++) {
        var block = document.createElement('div'); block.className = 'wx-day';
        add(block, 'wx-day-name', dayName(daily.time[i]));
        var values = document.createElement('div'); values.className = 'wx-day-values';
        add(values, 'wx-day-icon').innerHTML = icon(weather(daily.weather_code[i], 1)[1]);
        add(values, 'wx-high', degrees(daily.temperature_2m_max[i]));
        add(values, 'wx-low', degrees(daily.temperature_2m_min[i]));
        block.appendChild(values); days.appendChild(block);
      }
    }
    days.style.display = days.childNodes.length ? '' : 'none';
    text('stamp', (cached ? 'Cached \u00b7 ' : 'Updated ') + clockStamp(r));
    card.setAttribute('title', 'Model-based weather for Staines-upon-Thames. Times are Europe/London.');
  }
  function unavailable() {
    card.setAttribute('data-weather-state', 'unavailable');
    text('temp', '\u2014'); text('condition', 'Weather unavailable');
    text('feels', 'Celsius \u00b7 mph'); text('detail', 'Automatic retry; Home still works');
    text('stamp', 'No recent data'); el('days').innerHTML = ''; el('icon').innerHTML = icon('cloud');
  }
  function schedule(ms) { clearTimeout(timer); timer = setTimeout(tick, ms); }
  function tick() {
    if (document.hidden) { schedule(60000); return; }
    if (saved) render();
    if (busy) return;
    if (Date.now() < nextDue) { schedule(Math.min(60000, nextDue - Date.now())); return; }
    busy = true;
    var x, completed = false;
    function finish(ok, payload, rateLimited) {
      if (completed) return;
      completed = true; busy = false;
      if (ok) {
        saved = { savedAt: Date.now(), payload: payload }; failed = false;
        nextDue = Date.now() + REFRESH_MS;
        try { localStorage.setItem(CACHE_KEY, JSON.stringify(saved)); } catch (ignore) {}
        render();
      } else {
        failed = true; nextDue = Date.now() + (rateLimited ? REFRESH_MS : RETRY_MS);
        if (usable(saved)) render(); else unavailable();
      }
      schedule(60000);
    }
    try {
      x = new XMLHttpRequest(); x.open('GET', URL, true);
      x.timeout = TIMEOUT_MS; x.withCredentials = false;
      x.onload = function () {
        var r = null;
        try { r = JSON.parse(x.responseText); } catch (ignore) {}
        var candidate = { savedAt: Date.now(), payload: r };
        finish(x.status === 200 && usable(candidate), r, x.status === 429);
      };
      x.onerror = x.ontimeout = x.onabort = function () { finish(false); };
      x.send(null);
    } catch (ignore) { finish(false); }
  }
  try {
    var previous = JSON.parse(localStorage.getItem(CACHE_KEY) || 'null');
    if (usable(previous)) { saved = previous; nextDue = previous.savedAt + REFRESH_MS; render(); }
  } catch (ignore) {}
  el('icon').innerHTML = icon(saved ? weather(saved.payload.current.weather_code, saved.payload.current.is_day)[1] : 'cloud');
  document.addEventListener('visibilitychange', function () { if (!document.hidden) schedule(1000); });
  document.addEventListener('webOSRelaunch', function () { schedule(1000); });
  window.addEventListener('online', function () { nextDue = 0; schedule(1000); });
  // Give the launcher's initial catalogue and watchdog heartbeat priority.
  schedule(2000);
}());
/* END DNDGAMES-CLEAN-WEATHER-V21 SCRIPT */
