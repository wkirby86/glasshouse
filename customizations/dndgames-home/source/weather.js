/* DNDGAMES-WEATHER-LOCATION-V23 SCRIPT
 * Weather preferences live in this Home webview's localStorage, not home.json.
 * Search is explicit, via Open-Meteo/GeoNames; no GPS, API key or credentials.
 * ES5. Core catalogue, hidden items, takeover and heartbeat stay independent.
 */
(function () {
  'use strict';
  if (window.__dndWeatherLocationV23) return;
  window.__dndWeatherLocationV23 = true;
  var card = document.getElementById('dnd-weather');
  if (!card) return;
  var REFRESH_MS = 15 * 60 * 1000, MAX_AGE_MS = 2 * 60 * 60 * 1000;
  var RETRY_MS = 5 * 60 * 1000, TIMEOUT_MS = 10000;
  var SETTINGS_KEY = 'dnd.glasshouse.weather.settings.v1';
  var DEFAULT_LOCATION = { name: 'Staines-upon-Thames', country: 'United Kingdom',
    countryCode: 'GB', region: 'England', latitude: 51.434, longitude: -0.5114, timezone: 'Europe/London' };
  var location = DEFAULT_LOCATION;
  var saved = null, nextDue = 0, busy = false, failed = false, timer = null;
  var forecastRequest = null, generation = 0;
  var panel = document.getElementById('dnd-weather-settings');
  var changeButton = document.getElementById('dnd-wx-change');
  var searchInput = document.getElementById('dnd-location-query');
  var searchButton = document.getElementById('dnd-location-search');
  var saveButton = document.getElementById('dnd-location-save');
  var resultsBox = document.getElementById('dnd-location-results');
  var dialogOpen = false, controlFocused = false, selection = null, results = [];
  var searchRequest = null, searchRevision = 0, searchBlockedUntil = 0;
  var swallowed = {}, lastFocus = null;
  function el(id) { return document.getElementById('dnd-wx-' + id); }
  function text(id, value) { var e = el(id); if (e) e.textContent = value; }
  function numeric(n) { return typeof n === 'number' && isFinite(n); }
  function degrees(n) { return numeric(n) ? String(Math.round(n)) + '\u00b0' : '\u2014'; }
  function clockStamp(r) { return r.current.time.slice(11, 16); }
  function safeText(s, max) { return typeof s === 'string' && s.length > 0 && s.length <= max && !/[\x00-\x1f\x7f]/.test(s); }
  function validLocation(p) {
    return !!(p && safeText(p.name, 120) && safeText(p.country, 120) &&
      typeof p.countryCode === 'string' && /^[A-Z]{2}$/.test(p.countryCode) &&
      typeof p.region === 'string' && p.region.length <= 120 && !/[\x00-\x1f\x7f]/.test(p.region) &&
      numeric(p.latitude) && p.latitude >= -90 && p.latitude <= 90 &&
      numeric(p.longitude) && p.longitude >= -180 && p.longitude <= 180 &&
      typeof p.timezone === 'string' && p.timezone.length <= 100 &&
      /^(auto|UTC|GMT|[A-Za-z_]+(?:\/[A-Za-z0-9_+\-]+){1,3})$/.test(p.timezone));
  }
  function cleanLocation(p) {
    return {name:p.name,country:p.country,countryCode:p.countryCode,region:p.region,
      latitude:p.latitude,longitude:p.longitude,timezone:p.timezone};
  }
  function locationKey(p) { return [p.latitude, p.longitude, p.timezone, 'celsius', 'mph'].join('|'); }
  function cacheKey(p) { return 'dnd.glasshouse.weather.v23.' + locationKey(p); }
  function readLocation() {
    try {
      var value = JSON.parse(localStorage.getItem(SETTINGS_KEY) || 'null');
      if (value && value.version === 1 && validLocation(value.location)) return cleanLocation(value.location);
    } catch (ignore) {}
    return cleanLocation(DEFAULT_LOCATION);
  }
  function label(p) { return p.name + (p.region ? ', ' + p.region : '') + ', ' + p.country; }
  function renderPlace() {
    text('place', location.name); text('country', location.countryCode === 'GB' ? 'UK' : location.countryCode);
    el('place').setAttribute('title', label(location));
    card.setAttribute('aria-label', 'Weather for ' + label(location));
    document.getElementById('dnd-location-current').textContent = 'Current: ' + label(location);
  }
  function forecastURL(p) {
    return 'https://api.open-meteo.com/v1/forecast?latitude=' + encodeURIComponent(p.latitude) +
      '&longitude=' + encodeURIComponent(p.longitude) +
      '&current=temperature_2m,apparent_temperature,is_day,weather_code,wind_speed_10m' +
      '&daily=weather_code,temperature_2m_max,temperature_2m_min' +
      '&temperature_unit=celsius&wind_speed_unit=mph&timezone=' + encodeURIComponent(p.timezone) + '&forecast_days=4';
  }
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
    card.setAttribute('title', 'Model-based weather for ' + location.name + '. Times: ' + location.timezone + '.');
  }
  function unavailable() {
    card.setAttribute('data-weather-state', 'unavailable');
    text('temp', '\u2014'); text('condition', 'Weather unavailable');
    text('feels', 'Celsius \u00b7 mph'); text('detail', 'Automatic retry; Home still works');
    text('stamp', 'No recent data'); el('days').innerHTML = ''; el('icon').innerHTML = icon('cloud');
  }

  function loading() {
    card.setAttribute('data-weather-state', 'loading');
    text('temp', '\u2014'); text('condition', 'Loading weather');
    text('feels', 'Celsius \u00b7 mph'); text('detail', 'Connecting to Open-Meteo\u2026');
    text('stamp', 'Waiting for data'); el('days').innerHTML = ''; el('icon').innerHTML = icon('cloud');
  }
  function readCache() {
    saved = null;
    try {
      var previous = JSON.parse(localStorage.getItem(cacheKey(location)) || 'null');
      if (previous && previous.locationKey === locationKey(location) && usable(previous)) {
        saved = previous; nextDue = previous.savedAt + REFRESH_MS;
      }
    } catch (ignore) {}
    if (saved) render(); else loading();
  }
  function schedule(ms) { clearTimeout(timer); timer = setTimeout(tick, ms); }
  function tick() {
    if (document.hidden) { schedule(60000); return; }
    if (saved) render();
    if (busy) return;
    if (Date.now() < nextDue) { schedule(Math.min(60000, nextDue - Date.now())); return; }
    busy = true;
    var x, completed = false, token = generation, requestKey = locationKey(location);
    function finish(ok, payload, rateLimited) {
      if (completed || token !== generation || requestKey !== locationKey(location)) return;
      completed = true; busy = false; forecastRequest = null;
      if (ok) {
        saved = {savedAt:Date.now(),payload:payload,locationKey:requestKey}; failed = false;
        nextDue = Date.now() + REFRESH_MS;
        try { localStorage.setItem(cacheKey(location), JSON.stringify(saved)); } catch (ignore) {}
        render();
      } else {
        failed = true; nextDue = Date.now() + (rateLimited ? REFRESH_MS : RETRY_MS);
        if (usable(saved)) render(); else unavailable();
      }
      schedule(60000);
    }
    try {
      x = new XMLHttpRequest(); forecastRequest = x;
      x.open('GET', forecastURL(location), true);
      x.timeout = TIMEOUT_MS; x.withCredentials = false;
      x.onload = function () {
        var r = null;
        try { r = JSON.parse(x.responseText); } catch (ignore) {}
        finish(x.status === 200 && usable({savedAt:Date.now(),payload:r}), r, x.status === 429);
      };
      x.onerror = x.ontimeout = x.onabort = function () { finish(false); };
      x.send(null);
    } catch (ignore) { finish(false); }
  }
  function applyLocation(next) {
    generation++;
    if (forecastRequest) { try { forecastRequest.abort(); } catch (ignore) {} }
    forecastRequest = null; busy = false; failed = false; nextDue = 0;
    clearTimeout(timer);
    var oldKey = cacheKey(location);
    location = cleanLocation(next);
    if (oldKey !== cacheKey(location)) {
      try { localStorage.removeItem(oldKey); } catch (ignore) {}
    }
    renderPlace(); readCache(); schedule(150);
  }
  function status(message, error) {
    var e = document.getElementById('dnd-location-status');
    e.textContent = message; e.setAttribute('data-error', error ? '1' : '0');
  }
  function stopSearch() {
    searchRevision++;
    if (searchRequest) { try { searchRequest.abort(); } catch (ignore) {} }
    searchRequest = null; searchButton.disabled = false;
    resultsBox.setAttribute('aria-busy', 'false');
  }
  function allowed() {
    var stage = document.getElementById('stage');
    return stage && !/\b(arranging|recents)\b/.test(stage.className) && !document.hidden;
  }
  function focusControl() {
    if (!allowed()) return false;
    controlFocused = true;
    document.body.setAttribute('data-dnd-weather-focus', '1');
    changeButton.focus();
    return true;
  }
  function leaveControl() {
    controlFocused = false;
    document.body.removeAttribute('data-dnd-weather-focus');
    if (document.activeElement === changeButton) changeButton.blur();
  }
  function openDialog() {
    if (!allowed()) return;
    if (dialogOpen) { searchInput.focus(); return; }
    lastFocus = document.activeElement;
    dialogOpen = true; selection = null; results = [];
    saveButton.disabled = true; resultsBox.innerHTML = ''; searchInput.value = location.name;
    panel.style.display = 'block'; panel.setAttribute('aria-hidden', 'false');
    document.body.setAttribute('data-dnd-weather-focus', '1');
    renderPlace(); status('Enter a town or postcode, then choose Search.');
    searchInput.focus(); searchInput.select();
  }
  function closeDialog(restoreFocus) {
    if (!dialogOpen) return;
    stopSearch(); dialogOpen = false; selection = null;
    panel.style.display = 'none'; panel.setAttribute('aria-hidden', 'true');
    if (document.activeElement && panel.contains(document.activeElement)) document.activeElement.blur();
    if (restoreFocus !== false && lastFocus === changeButton) focusControl(); else leaveControl();
  }
  function searchLocations() {
    if (!dialogOpen) return;
    var query = searchInput.value.replace(/^\s+|\s+$/g, '');
    if (query.length < 2 || query.length > 100 || /[\x00-\x1f\x7f]/.test(query)) {
      status('Use 2 to 100 characters for a town or postcode.', true); return;
    }
    if (Date.now() < searchBlockedUntil) {
      status('Search is temporarily limited. Please try again in a minute.', true); return;
    }
    stopSearch();
    var token = searchRevision;
    selection = null; results = []; saveButton.disabled = true; resultsBox.innerHTML = '';
    searchButton.disabled = true; resultsBox.setAttribute('aria-busy', 'true');
    status('Searching\u2026');
    var x, done = false;
    function complete(ok, response, code) {
      if (done || token !== searchRevision || !dialogOpen) return;
      done = true; searchRequest = null; searchButton.disabled = false;
      resultsBox.setAttribute('aria-busy', 'false');
      if (!ok) {
        if (code === 429) searchBlockedUntil = Date.now() + 60000;
        status(code === 429 ? 'Search is temporarily limited. Try again in a minute.' :
          'Location search is unavailable. Your saved location has not changed.', true);
        return;
      }
      var list = response.results || [];
      for (var i = 0; i < Math.min(8, list.length); i++) {
        var r = list[i], candidate = {name:r.name,country:r.country,countryCode:r.country_code,
          region:r.admin1 || '',latitude:r.latitude,longitude:r.longitude,timezone:r.timezone || 'auto'};
        if (validLocation(candidate)) results.push(cleanLocation(candidate));
      }
      if (!results.length) {
        status('No matching locations. Try the nearest town, or add a country after a comma.'); return;
      }
      results.forEach(function (p, index) {
        var b = document.createElement('button'); b.type = 'button'; b.className = 'dnd-location-result';
        b.setAttribute('aria-pressed', 'false'); b.setAttribute('data-result', String(index));
        var title = document.createElement('span'); title.className = 'location-name'; title.textContent = p.name;
        var sub = document.createElement('span'); sub.className = 'location-region';
        sub.textContent = (p.region ? p.region + ', ' : '') + p.country + ' \u00b7 ' + p.timezone;
        b.appendChild(title); b.appendChild(sub);
        b.addEventListener('click', function () { choose(index); }); resultsBox.appendChild(b);
      });
      status('Choose a location, then select Save location. Nothing changes until you save.');
      var active = document.activeElement;
      if (active === searchInput || active === searchButton || active === document.body) resultsBox.firstChild.focus();
    }
    try {
      x = new XMLHttpRequest(); searchRequest = x;
      x.open('GET', 'https://geocoding-api.open-meteo.com/v1/search?name=' + encodeURIComponent(query) +
        '&count=8&language=en&format=json', true);
      x.timeout = TIMEOUT_MS; x.withCredentials = false;
      x.onload = function () {
        var r = null;
        try { r = JSON.parse(x.responseText); } catch (ignore) {}
        complete(x.status === 200 && r && !r.error && (!r.results || Object.prototype.toString.call(r.results) === '[object Array]'), r, x.status);
      };
      x.onerror = x.ontimeout = x.onabort = function () { complete(false, null, 0); };
      x.send(null);
    } catch (ignore) { complete(false, null, 0); }
  }
  function choose(index) {
    if (!results[index]) return;
    selection = results[index];
    var buttons = resultsBox.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) buttons[i].setAttribute('aria-pressed', i === index ? 'true' : 'false');
    saveButton.disabled = false;
    status('Selected: ' + label(selection) + '. Select Save location to apply.');
    saveButton.focus();
  }
  function saveLocation() {
    if (!selection || !validLocation(selection)) return;
    var next = cleanLocation(selection), encoded = JSON.stringify({version:1,location:next});
    try {
      localStorage.setItem(SETTINGS_KEY, encoded);
      if (localStorage.getItem(SETTINGS_KEY) !== encoded) throw new Error('Storage verification failed');
    } catch (ignore) {
      status('This Home view cannot save preferences. Location unchanged. Check browser storage and retry.', true);
      return;
    }
    applyLocation(next); closeDialog(true);
  }
  function consume(e) {
    e.preventDefault();
    if (e.stopImmediatePropagation) e.stopImmediatePropagation(); else e.stopPropagation();
    if (e.type === 'keydown') swallowed[e.keyCode] = true;
  }
  function focusables() {
    var nodes = panel.querySelectorAll('input,button'), out = [];
    for (var i = 0; i < nodes.length; i++) if (!nodes[i].disabled && nodes[i].offsetWidth) out.push(nodes[i]);
    return out;
  }
  function stepFocus(delta) {
    var nodes = focusables(), index = nodes.indexOf(document.activeElement);
    if (!nodes.length) return;
    index = (index + delta + nodes.length) % nodes.length;
    nodes[index].focus();
    if (nodes[index].className === 'dnd-location-result') {
      var node = nodes[index], top = node.offsetTop;
      if (top < resultsBox.scrollTop) resultsBox.scrollTop = top;
      if (top + node.offsetHeight > resultsBox.scrollTop + resultsBox.clientHeight) resultsBox.scrollTop = top + node.offsetHeight - resultsBox.clientHeight;
    }
  }
  function weatherKeys(e) {
    var k = e.keyCode;
    if (e.type === 'keyup') {
      if (swallowed[k]) { delete swallowed[k]; consume(e); }
      return;
    }
    if (!dialogOpen && k === 406 && allowed()) { consume(e); focusControl(); openDialog(); return; }
    if (dialogOpen) {
      if (k === 461 || k === 27) { consume(e); closeDialog(true); return; }
      if (k === 9) { consume(e); stepFocus(e.shiftKey ? -1 : 1); return; }
      if (k === 13) {
        consume(e);
        if (e.repeat) return;
        if (document.activeElement === searchInput) searchLocations();
        else if (document.activeElement && document.activeElement.tagName === 'BUTTON' && !document.activeElement.disabled) document.activeElement.click();
        return;
      }
      if (k === 38 || k === 40 || ((k === 37 || k === 39) && document.activeElement !== searchInput)) {
        consume(e); stepFocus(k === 38 || k === 37 ? -1 : 1); return;
      }
      // Typing and caret movement belong to the input, never to the launcher.
      if (e.stopImmediatePropagation) e.stopImmediatePropagation(); else e.stopPropagation();
      return;
    }
    if (controlFocused) {
      if (k === 13) { consume(e); if (!e.repeat) openDialog(); }
      else if (k === 40 || k === 461 || k === 27) { consume(e); leaveControl(); }
      else if (k === 37 || k === 38 || k === 39) consume(e);
    }
  }
  changeButton.addEventListener('click', openDialog);
  changeButton.addEventListener('focus', function () { controlFocused = true; document.body.setAttribute('data-dnd-weather-focus', '1'); });
  searchButton.addEventListener('click', searchLocations);
  searchInput.addEventListener('input', function () {
    stopSearch(); selection = null; results = []; saveButton.disabled = true; resultsBox.innerHTML = '';
    status('Choose Search to find matching locations.');
  });
  saveButton.addEventListener('click', saveLocation);
  document.getElementById('dnd-location-cancel').addEventListener('click', function () { closeDialog(true); });
  document.getElementById('dnd-location-close').addEventListener('click', function () { closeDialog(true); });
  panel.addEventListener('click', function (e) { if (e.target === panel) closeDialog(true); });
  // Capture before Glasshouse's document handlers, without replacing them.
  window.addEventListener('keydown', weatherKeys, true);
  window.addEventListener('keyup', weatherKeys, true);
  window.addEventListener('mousemove', function (e) {
    if (controlFocused && !dialogOpen && !card.contains(e.target)) leaveControl();
    if (dialogOpen) { if (e.stopImmediatePropagation) e.stopImmediatePropagation(); else e.stopPropagation(); }
  }, true);
  window.addEventListener('click', function (e) {
    // Pointer movement back to the dock releases weather-button focus.
    if (controlFocused && !dialogOpen && !card.contains(e.target)) leaveControl();
  }, true);
  panel.addEventListener('click', function (e) { e.stopPropagation(); });
  card.addEventListener('click', function (e) { if (e.target === changeButton) e.stopPropagation(); });
  window.DNDWeatherLocation = { focusControl: focusControl };
  location = readLocation(); renderPlace(); readCache();
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { closeDialog(false); leaveControl(); stopSearch(); }
    else schedule(1000);
  });
  document.addEventListener('webOSRelaunch', function () { closeDialog(false); leaveControl(); schedule(1000); });
  window.addEventListener('online', function () { nextDue = 0; schedule(1000); });
  window.addEventListener('storage', function (e) { if (e.key === SETTINGS_KEY) { closeDialog(false); applyLocation(readLocation()); } });
  schedule(2000);
}());
/* END DNDGAMES-WEATHER-LOCATION-V23 SCRIPT */
