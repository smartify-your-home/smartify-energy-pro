// PV surface editor card (custom:smartify-energy-pv-card)
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {JSDOM} = require('jsdom');
const fs = require('node:fs');
const source = fs.readFileSync('custom_components/smartify_energy/www/smartify-energy-plan-card.js', 'utf8');

const LAT = 47.98, LON = 13.25, M_LAT = 1 / 111320, M_LON = M_LAT / 0.6692;
const pt = (e, n) => [LAT + n * M_LAT, LON + e * M_LON];
const RECT = [pt(0, 0), pt(10, 0), pt(10, 6), pt(0, 6)];

function load() {
  const dom = new JSDOM('<div id="root"></div>', {runScripts: 'outside-only', pretendToBeVisual: true});
  let n = 0;
  dom.window.URL.createObjectURL = () => `blob:tile-${++n}`;
  dom.window.URL.revokeObjectURL = () => {};
  dom.window.eval(source + '\nwindow.pv={pvSurfaceAzimuth,pvDefaultEdge,pvAreaM2,pvKwp};');
  return dom;
}
const tick = () => new Promise(r => setTimeout(r, 0));

test('azimuth from drawing matches the Python implementation', () => {
  const {pv} = load().window;
  const near = (a, b) => assert.ok(Math.abs(a - b) <= 0.5, `${a} != ${b}`);
  near(pv.pvSurfaceAzimuth({kind: 'area', points: RECT, edge: 0}, 19), 180);
  near(pv.pvSurfaceAzimuth({kind: 'area', points: RECT, edge: 1}, 19), 90);
  near(pv.pvSurfaceAzimuth({kind: 'area', points: RECT, edge: 3}, 19), 270);
  near(pv.pvSurfaceAzimuth({kind: 'area', points: RECT, edge: 0, flip: true}, 19), 0);
  near(pv.pvSurfaceAzimuth({kind: 'area', points: [...RECT].reverse(), edge: 2}, 19), 180);
  near(pv.pvSurfaceAzimuth({kind: 'line', points: [pt(0, 0), pt(10, 0)]}, 19), 180);
  near(pv.pvSurfaceAzimuth({kind: 'line', points: [pt(0, 0), pt(10, 0)], flip: true}, 19), 0);
  near(pv.pvSurfaceAzimuth({kind: 'area', points: [pt(0, 0), pt(7.07, 7.07), pt(2.83, 11.31), pt(-4.24, 4.24)], edge: 0}, 19), 135);
  assert.equal(pv.pvSurfaceAzimuth({kind: 'manual', azimuth: 265}, 19), 265);
  assert.equal(pv.pvDefaultEdge(RECT, 19), 0);
  assert.ok(Math.abs(pv.pvAreaM2(RECT, 19) - 60) < 1.5);
  assert.equal(pv.pvKwp({input: 'modules', modules: 8, module_wp: 380}), 3.04);
  assert.equal(pv.pvKwp({input: 'kwp', kwp: 2.66}), 2.66);
});

function card(dom, {admin = true, map = null, surfaces} = {}) {
  const calls = [];
  const layout = {entry_id: 'e1', solar_mode: 'calculated', max_surfaces: 4, home: {lat: LAT, lon: LON},
    zoom: {default: 19, min: 17, max: 20}, attribution: 'Luftbild: basemap.at (CC BY 4.0)', map,
    surfaces: surfaces ?? [{id: 's1', name: 'Fläche 1', kind: 'manual', points: [], edge: 0, flip: false, tilt: 90,
      azimuth: 190, input: 'kwp', kwp: 3.04, modules: 0, module_wp: 0, area_m2: null}]};
  const hass = {user: {is_admin: admin}, callWS: async msg => {
    calls.push(msg);
    if (msg.type === 'smartify_energy/pv_layout') return JSON.parse(JSON.stringify(layout));
    if (msg.type === 'smartify_energy/pv_layout/save') return {surfaces: msg.surfaces, total_kwp: 1};
    if (msg.type === 'smartify_energy/pv_map/reload') throw new Error('offline');
  }};
  const el = dom.window.document.createElement('smartify-energy-pv-card');
  dom.window.document.body.append(el);
  el.setConfig({title: 'PV-Flächen'});
  el.hass = hass;
  return {el, calls};
}

test('legacy surfaces are editable, saving sends the edited surfaces', async () => {
  const dom = load();
  dom.window.confirm = () => true;
  const {el, calls} = card(dom);
  await tick(); await tick();
  const root = el.shadowRoot;
  assert.match(root.textContent, /nicht eingezeichnet/);
  assert.equal(root.querySelector('[data-f="azimuth"]'), null, 'rows start collapsed');
  root.querySelector('.surf [data-act="toggle"]').click();
  assert.equal(root.querySelector('[data-f="azimuth"]').value, '190');
  // switch to modules × Wp
  const sel = root.querySelector('[data-f="input"]');
  sel.value = 'modules'; sel.dispatchEvent(new dom.window.Event('change'));
  const mods = root.querySelector('[data-f="modules"]'), wp = root.querySelector('[data-f="module_wp"]');
  assert.ok(mods && wp, 'modules and Wp inputs shown');
  mods.value = '8'; mods.dispatchEvent(new dom.window.Event('change'));
  root.querySelector('[data-f="module_wp"]').value = '380';
  root.querySelector('[data-f="module_wp"]').dispatchEvent(new dom.window.Event('change'));
  assert.match(root.querySelector('.surf .chip').textContent, /3,04 kWp/);
  // bifacial
  const bi = root.querySelector('[data-f="bifacial"]');
  bi.checked = true; bi.dispatchEvent(new dom.window.Event('change'));
  assert.equal(root.querySelector('[data-f="bifaciality"]').value, '0.7');
  assert.match(root.querySelector('.surf .s-head').textContent, /bifazial/);
  assert.match(root.textContent, /nicht gespeichert/);
  root.querySelector('[data-act="save"]').click();
  await tick(); await tick();
  const save = calls.find(c => c.type === 'smartify_energy/pv_layout/save');
  assert.deepEqual(JSON.parse(JSON.stringify(save.surfaces.map(s => [s.input, s.modules, s.module_wp, s.azimuth, s.bifacial]))), [['modules', 8, 380, 190, true]]);
  assert.match(root.textContent, /Gespeichert/);
});

test('first open without stored photo downloads it once, failure is shown and grid stays usable', async () => {
  const dom = load();
  const {el, calls} = card(dom);
  await tick(); await tick(); await tick();
  assert.equal(calls.filter(c => c.type === 'smartify_energy/pv_map/reload').length, 1);
  assert.match(el.shadowRoot.textContent, /offline/);
  assert.match(el.shadowRoot.textContent, /kein Luftbild/);
  el.hass = el._hass;   // further hass updates never reload
  await tick();
  assert.equal(calls.filter(c => c.type === 'smartify_energy/pv_map/reload').length, 1);
});

test('stored photo is not downloaded again and drawn area shows azimuth arrow and eave', async () => {
  const dom = load();
  const map = {lat: LAT, lon: LON, zoom: 19, fetched: '2026-11-11T10:00:00Z', attribution: 'Luftbild: basemap.at (CC BY 4.0)',
    tiles: [{x: Math.floor((LON + 180) / 360 * 2 ** 19),
      y: Math.floor((1 - Math.log(Math.tan(LAT * Math.PI / 180) + 1 / Math.cos(LAT * Math.PI / 180)) / Math.PI) / 2 * 2 ** 19), data: '/9j/'}]};
  const {el, calls} = card(dom, {map, surfaces: [{id: 'a', name: 'Süd', kind: 'area', points: RECT, edge: 0, flip: false,
    tilt: 35, azimuth: 180, input: 'kwp', kwp: 5, modules: 0, module_wp: 0, area_m2: 60}]});
  await tick(); await tick();
  assert.equal(calls.filter(c => c.type === 'smartify_energy/pv_map/reload').length, 0);
  const root = el.shadowRoot;
  assert.ok(root.querySelector('polygon[data-surface="a"]'));
  assert.equal(root.querySelector('svg image').getAttribute('href'), 'blob:tile-1');
  // Regression 0.3.64: absolute Web-Mercator pixels (~7e7) exceed SVG float32 precision → empty map.
  const coords = [...root.querySelectorAll('svg image, svg polygon')].flatMap(n =>
    [n.getAttribute('x'), n.getAttribute('y'), ...(n.getAttribute('points') || '').split(/[ ,]/)].filter(Boolean).map(Number));
  assert.ok(coords.length && coords.every(v => Math.abs(v) < 1e6), 'svg uses local coordinates');
  assert.ok(root.querySelector('svg').getAttribute('viewBox').split(' ').every(v => Math.abs(Number(v)) < 1e6));
  assert.match(root.querySelector('svg text').textContent, /180° S/);
  // label sits outside at the arrow tip (south → below the eave), not on the area centroid
  const label = root.querySelector('svg text.pv-label'), poly = root.querySelector('polygon[data-surface="a"]');
  const ys = poly.getAttribute('points').split(' ').map(p => Number(p.split(',')[1]));
  assert.ok(Number(label.getAttribute('y')) > Math.max(...ys), 'south label below the polygon');
  assert.equal(label.getAttribute('dominant-baseline'), 'hanging');
  assert.match(root.textContent, /Luftbild neu laden/);
  assert.match(root.textContent, /basemap\.at/);
});

test('non-admin users see the layout read-only', async () => {
  const dom = load();
  const {el, calls} = card(dom, {admin: false});
  await tick(); await tick();
  const root = el.shadowRoot;
  assert.equal(calls.filter(c => c.type !== 'smartify_energy/pv_layout').length, 0);
  assert.equal(root.querySelector('[data-act="save"]'), null);
  root.querySelector('.surf [data-act="toggle"]').click();
  assert.ok(root.querySelector('[data-f="tilt"]').disabled);
  assert.match(root.textContent, /Nur Administratoren/);
});

test('hass setter never throws even if the backend is missing', async () => {
  const dom = load();
  const el = dom.window.document.createElement('smartify-energy-pv-card');
  dom.window.document.body.append(el);
  el.setConfig({});
  assert.doesNotThrow(() => { el.hass = {user: {is_admin: true}, callWS: async () => { throw new Error('unknown command'); }}; });
  await tick(); await tick();
  assert.match(el.shadowRoot.textContent, /konnten nicht geladen werden/);
});

test('wide cards place the list right of the map, list rows collapse', async () => {
  const dom = load();
  const {el} = card(dom, {surfaces: [{id: 'a', name: 'Süd', kind: 'area', points: RECT, edge: 0, flip: false, tilt: 35,
    azimuth: 180, input: 'kwp', kwp: 5, modules: 0, module_wp: 0, area_m2: 60}]});
  await tick(); await tick();
  const root = el.shadowRoot;
  assert.ok(root.querySelector('.layout > .main .map') && root.querySelector('.layout > .side .surf'));
  assert.match(source, /@container \(min-width: 860px\)[^}]*grid-template-columns:minmax\(0,1fr\) minmax\(300px,380px\)/);
  assert.match(root.querySelector('.surf .s-head').textContent, /180° S · 35°/);
  const tog = root.querySelector('.surf .tog');
  assert.equal(tog.getAttribute('aria-expanded'), 'false');
  tog.click();
  assert.equal(root.querySelector('.surf .tog').getAttribute('aria-expanded'), 'true');
  assert.ok(root.querySelector('[data-f="tilt"]'));
  root.querySelector('.surf .tog').click();
  assert.equal(root.querySelector('[data-f="tilt"]'), null);
});


test('legacy aerial photo at wrong location is recentered to Home Assistant, without changing PV arrays', async()=>{
  const dom=load();
  const wrong={lat:48.45,lon:16.3,zoom:19,source:'legacy',fetched:'2026-11-11T12:00:00Z',
    attribution:'Luftbild: basemap.at',tiles:[]};
  const {el,calls}=card(dom,{map:wrong});
  await tick();await tick();await tick();
  const reload=calls.find(x=>x.type==='smartify_energy/pv_map/reload');
  assert.ok(reload,'old map location triggers automatic replacement');
  assert.equal(reload.lat,LAT);
  assert.equal(reload.lon,LON);
  assert.equal(reload.source,'home');
  assert.equal(el._surfaces.length,1,'saved legacy PV areas untouched');
});

test('address input geocodes only on click and centers imagery on lookup result', async()=>{
  const dom=load();
  const map={lat:LAT,lon:LON,zoom:19,source:'home',fetched:'2026-11-11T12:00:00Z',
    attribution:'Luftbild: basemap.at',tiles:[]};
  const {el,calls}=card(dom,{map});
  await tick();await tick();
  let geocodes=0;
  const originalWS=el._hass.callWS;
  el._hass.callWS=async msg=>{
    calls.push(msg);
    if(msg.type==='smartify_energy/pv_map/geocode'){
      geocodes++;
      return {lat:48.21,lon:16.36,display_name:'Wien'};
    }
    if(msg.type==='smartify_energy/pv_map/reload')
      return {map:{...map,lat:msg.lat,lon:msg.lon,source:msg.source}};
    return originalWS(msg);
  };
  const input=el.shadowRoot.querySelector('[data-map-address]');
  assert.ok(input);
  input.value='Wien, Österreich';
  input.dispatchEvent(new dom.window.Event('input'));
  assert.equal(geocodes,0,'never geocode on each keystroke');
  el.shadowRoot.querySelector('[data-act="address"]').click();
  await tick();await tick();await tick();
  assert.equal(geocodes,1);
  assert.equal(calls.findLast(x=>x.type==='smartify_energy/pv_map/reload').source,'address');
  assert.equal(el._data.map.lat,48.21);
  assert.equal(el._surfaces.length,1);
  el.shadowRoot.querySelector('[data-act="home"]').click();
  await tick();await tick();await tick();
  assert.equal(calls.findLast(x=>x.type==='smartify_energy/pv_map/reload').lat,LAT);
  assert.equal(calls.findLast(x=>x.type==='smartify_energy/pv_map/reload').source,'home');
});

test('zoom and pan trigger a new tile request with correct zoom and center',async()=>{
  const dom=load();
  const x=Math.floor((LON+180)/360*2**19);
  const y=Math.floor((1-Math.log(Math.tan(LAT*Math.PI/180)+1/Math.cos(LAT*Math.PI/180))/Math.PI)/2*2**19);
  const map={lat:LAT,lon:LON,zoom:19,source:'home',fetched:'2026-11-11T12:00:00Z',
    attribution:'Luftbild: basemap.at',
    tiles:Array.from({length:25},(_,i)=>({x:x+Math.floor(i/5)-2,y:y+i%5-2,data:'/9j/'}))};
  const {el}=card(dom,{map});
  await tick();await tick();
  let pending=[];
  el._reloadMap=async(auto,target)=>{pending.push(target);};
  el._view={...el._view,w:300,h:220};
  el._maybeRefreshMap();
  assert.equal(pending.length,1);
  assert.equal(pending[0].zoom,20,'zoom in requests higher resolution tiles');
  pending=[];
  el._view={...el._view,w:1350,h:900};
  el._maybeRefreshMap();
  assert.equal(pending[0].zoom,18,'zoom out requests lower zoom tiles');
  pending=[];
  el._resetView();
  el._view.x=el._view.bounds.x0+20;
  el._maybeRefreshMap();
  assert.equal(pending.length,1,'pan outside tile coverage fetches shifted tiles');
  assert.equal(pending[0].zoom,19);
});


test('deleting surfaces renumbers default names but keeps ids and custom names', async () => {
  const dom=load(); dom.window.confirm=()=>true;
  const surface=(id,name)=>({id,name,kind:'manual',points:[],azimuth:180,tilt:30,input:'kwp',kwp:1});
  const {el}=card(dom,{surfaces:[surface('f1','Fläche 1'),surface('f2','Fläche 2'),surface('f3','Fläche 3'),surface('f4','Fläche 4')]});
  await tick();await tick();
  el._action('del','f1');el._action('del','f2');
  assert.deepEqual(el._surfaces.map(x=>x.name),['Fläche 1','Fläche 2']);
  assert.deepEqual(el._surfaces.map(x=>x.id),['f3','f4']);
  el._change('f3',{name:'Garage'});el._action('del','f4');
  assert.equal(el._surfaces[0].name,'Garage');
});
test('Photon suggestions choose coordinates without Nominatim lookup', async () => {
  const dom=load();
  const map={lat:LAT,lon:LON,zoom:19,source:'home',fetched:'2026-11-11T12:00:00Z',
    attribution:'Luftbild: basemap.at',tiles:[]};
  const {el,calls}=card(dom,{map});await tick();await tick();
  const original=el._hass.callWS;
  el._hass.callWS=async msg=>{
    calls.push(msg);
    if(msg.type==='smartify_energy/pv_map/suggest')
      return {results:[{lat:48.21,lon:16.36,display_name:'Wien, Österreich'}]};
    if(msg.type==='smartify_energy/pv_map/reload')
      return {map:{...map,lat:msg.lat,lon:msg.lon,source:msg.source}};
    return original(msg);
  };
  const input=el.shadowRoot.querySelector('[data-map-address]');
  input.value='Wie';input.dispatchEvent(new dom.window.Event('input'));
  await new Promise(resolve=>setTimeout(resolve,750));await tick();
  const suggestion=el.shadowRoot.querySelector('[data-suggest="0"]');
  assert.ok(suggestion);suggestion.click();await tick();await tick();
  assert.equal(calls.filter(x=>x.type==='smartify_energy/pv_map/geocode').length,0);
  assert.equal(calls.findLast(x=>x.type==='smartify_energy/pv_map/reload').lat,48.21);
});
