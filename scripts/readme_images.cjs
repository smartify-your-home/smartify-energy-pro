// Rendert die echte SEP-Karte mit HA-Default-Theme, Roboto und MDI-Icons für die README.
// Beispieldaten sind neutral (keine echte Installation).
// Einmalig:  npm i --no-save @mdi/js@7.4.47 @fontsource/roboto@5.1.0
// Aufruf:    node scripts/readme_images.cjs . docs/images
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const mdi = require('@mdi/js');

const [repo, out] = process.argv.slice(2);
const NOW = Date.parse('2026-06-21T10:40:00+02:00');
const cardSrc = fs.readFileSync(path.join(repo, 'custom_components/smartify_energy/www/smartify-energy-plan-card.js'), 'utf8');
const logo = fs.readFileSync(path.join(repo, 'custom_components/smartify_energy/www/sep-logo.png'));
const fontDir = path.join(path.dirname(require.resolve('@fontsource/roboto/package.json')), 'files');
const font = w => fs.readFileSync(path.join(fontDir, `roboto-latin-${w}-normal.woff2`));

const usedIcons = [...new Set([...cardSrc.matchAll(/mdi:[a-z0-9-]+/g)].map(m => m[0]).concat(
  ['mdi:washing-machine', 'mdi:dishwasher', 'mdi:ev-station', 'mdi:water-boiler', 'mdi:pool', 'mdi:cog']))];
const iconMap = {};
for (const name of usedIcons) {
  const key = 'mdi' + name.slice(4).split('-').map(p => p[0].toUpperCase() + p.slice(1)).join('');
  if (mdi[key]) iconMap[name] = mdi[key];
}

const page = `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Roboto;font-weight:400;src:url(/f/400.woff2)}
@font-face{font-family:Roboto;font-weight:500;src:url(/f/500.woff2)}
@font-face{font-family:Roboto;font-weight:700;src:url(/f/700.woff2)}
:root{--primary-color:#03a9f4;--text-primary-color:#fff;--primary-text-color:#212121;--secondary-text-color:#727272;
--card-background-color:#fff;--ha-card-background:#fff;--secondary-background-color:#f5f5f5;--divider-color:rgba(0,0,0,.12);
--success-color:#43a047;--error-color:#db4437;--warning-color:#ffa600;--ha-card-border-radius:12px;--paper-font-body1_-_font-family:Roboto;}
html,body{margin:0;background:#f3f3f3;font-family:Roboto,sans-serif;color:var(--primary-text-color);-webkit-font-smoothing:antialiased}
#wrap{padding:16px}
ha-card{display:block;background:var(--card-background-color);border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,.08);overflow:hidden}
ha-icon{display:inline-flex;width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px);vertical-align:middle;flex:none}
ha-icon svg{width:100%;height:100%;fill:currentColor}
</style></head><body><div id="wrap"></div><script>
window.ICONS=${JSON.stringify(iconMap)};
customElements.define('ha-icon',class extends HTMLElement{
  static get observedAttributes(){return['icon']}
  constructor(){super();this.attachShadow({mode:'open'});}
  connectedCallback(){this.r()} attributeChangedCallback(){this.r()}
  r(){const d=ICONS[this.getAttribute('icon')];
    this.shadowRoot.innerHTML='<style>:host{display:inline-flex;align-items:center;justify-content:center;vertical-align:middle;width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px);flex:none}svg{width:100%;height:100%;fill:currentColor;display:block}</style>'+(d?'<svg viewBox="0 0 24 24"><path d="'+d+'"/></svg>':'');}
});
customElements.define('ha-card',class extends HTMLElement{
  constructor(){super();this.attachShadow({mode:'open'}).innerHTML='<style>:host{display:block;background:var(--ha-card-background,var(--card-background-color,#fff));border-radius:var(--ha-card-border-radius,12px);box-shadow:0 2px 6px rgba(0,0,0,.08);overflow:hidden}</style><slot></slot>';}
});
</script></body></html>`;

// ---- Beispieldaten (neutral, typischer sonniger Tag) ----
function scenario(now) {
  const H = 3600e3;
  const iso = ms => new Date(ms).toISOString();
  const entities = {}, states = {}, devices = { hub: { name: 'Energiemanager' } };
  const add = (dev, id, key, state, attrs = {}, cat) => {
    entities[id] = { platform: 'smartify_energy', translation_key: key, device_id: dev, entity_id: id, entity_category: cat };
    states[id] = { state: String(state), attributes: attrs };
  };
  const modeOpts = { options: ['auto', 'observe', 'manual', 'off'] };
  // Kopf
  add('hub', 'sensor.sep_surplus', 'surplus', 2840, { unit_of_measurement: 'W' });
  add('hub', 'sensor.sep_surplus_avg', 'surplus_avg', 2610, { unit_of_measurement: 'W' });
  add('hub', 'sensor.sep_budget', 'budget', 5120, { unit_of_measurement: 'W' });
  add('hub', 'sensor.sep_budget_avg', 'budget_avg', 4870, { unit_of_measurement: 'W' });
  add('hub', 'sensor.sep_allocated', 'allocated', 2280, { unit_of_measurement: 'W' });
  add('hub', 'sensor.sep_forecast', 'forecast_today', 38.4, { unit_of_measurement: 'kWh', rest_heute_kwh: 17.9, morgen_kwh: 34.2 });
  add('hub', 'select.sep_mode', 'mode', 'auto', modeOpts);
  add('hub', 'number.sep_avg', 'avg_window', 8, { unit_of_measurement: 'min', friendly_name: 'Energiemanager Mittelungsfenster' }, 'config');
  add('hub', 'number.sep_tol', 'trend_tolerance', 100, { unit_of_measurement: 'W', friendly_name: 'Energiemanager Trendtoleranz' }, 'config');
  // PV-Plan: Glockenkurve ab aktueller Stunde
  const start = new Date(now); start.setMinutes(0, 0, 0);
  const stunden = [];
  for (let i = 0; i < 36; i++) {
    const t = start.getTime() + i * H, h = new Date(t).getHours() + 0.5;
    const pv = Math.max(0, Math.round(8200 * Math.sin(Math.PI * (h - 6) / 14.5) ** 1.6)) * (i >= 24 ? 0.92 : 1);
    const geraete = {};
    if (i === 0) Object.assign(geraete, { 'E-Auto': 2070, 'Geschirrspüler': 1850 });
    if (i === 1) Object.assign(geraete, { 'E-Auto': 3200, 'Waschmaschine': 2000 });
    if (i === 2) Object.assign(geraete, { 'E-Auto': 2500, 'Heizstab': 1500 });
    if (i === 3) Object.assign(geraete, { 'Heizstab': 2000, 'Poolpumpe': 650 });
    const used = Object.values(geraete).reduce((a, b) => a + b, 0);
    stunden.push({ zeit: iso(t), pv_w: Math.round(pv), frei_w: Math.max(0, Math.round(pv - 600 - used)), geraete });
  }
  add('hub', 'sensor.sep_plan', 'plan', 'Waschmaschine 13:00', { stunden, prognose_quelle: 'forecast_solar' });

  const common = (prio, extra) => ({ modus: 'auto', prioritaet: prio, trend_ready: true, history_avg_ready: true,
    trend_history_min: 14, trend_window_min: 1, ...extra });
  // 1 Waschmaschine – wartet auf PV
  devices.wm = { name: 'Waschmaschine', via_device_id: 'hub' };
  add('wm', 'sensor.wm_status', 'status', 'waiting', {icon:'mdi:washing-machine',...common(1, { geraetetyp: 'load', phase: 'wartet', status_code: 'waiting',
    reason: 'Programm erkannt – wartet auf PV (benötigt 2000 W)', aktuell_w: 1780, mittel_w: 1650, benoetigt_w: 2000,
    trend_mittel_w: 1820, trend_delta_w: 140, pflicht_start: iso(now + 3.4 * H) })});
  add('wm', 'sensor.wm_power', 'power', 3, { unit_of_measurement: 'W' });
  add('wm', 'select.wm_mode', 'mode', 'auto', modeOpts);
  add('wm', 'button.wm_start', 'start_now', 'unknown');
  add('wm', 'switch.wm_nachladen', 'nachladen', 'off');
  add('wm', 'button.wm_reset', 'reset', 'unknown');
  // 2 Geschirrspüler – läuft
  devices.gs = { name: 'Geschirrspüler', via_device_id: 'hub' };
  add('gs', 'sensor.gs_status', 'status', 'running', {icon:'mdi:dishwasher',...common(2, { geraetetyp: 'load', phase: 'laeuft', status_code: 'running',
    reason: 'Programm läuft – mit PV gestartet', aktuell_w: 3300, mittel_w: 3100, benoetigt_w: 1900, trend_mittel_w: 3250, trend_delta_w: 60 })});
  add('gs', 'sensor.gs_power', 'power', 1850, { unit_of_measurement: 'W' });
  add('gs', 'select.gs_mode', 'mode', 'auto', modeOpts);
  add('gs', 'button.gs_reset', 'reset', 'unknown');
  // 3 E-Auto – PV-Laden
  devices.ev = { name: 'E-Auto', via_device_id: 'hub' };
  add('ev', 'sensor.ev_status', 'status', 'charging_pv', {icon:'mdi:ev-station',...common(3, { geraetetyp: 'ev', status_code: 'charging_pv',
    reason: 'PV-Laden 9 A × 1', aktuell_w: 2300, mittel_w: 2180, benoetigt_w: 11040, soc: 58, voll_um: iso(now + 5.6 * H) })});
  add('ev', 'sensor.ev_power', 'power', 2070, { unit_of_measurement: 'W' });
  add('ev', 'select.ev_mode', 'mode', 'auto', { ...modeOpts, friendly_name: 'E-Auto Modus' });
  add('ev', 'select.ev_goal', 'goal', 'pv_only', { options: ['pv_only', 'km_until', 'days', 'now'], friendly_name: 'E-Auto Ladeziel' });
  add('ev', 'switch.ev_boost', 'boost', 'off', { friendly_name: 'E-Auto PV-Boost' });
  const evCfg = [
    ['number.ev_bf', 'boost_factor', 2, '×', 'Boost-Faktor'], ['number.ev_bh', 'boost_hours', 3, 'h', 'Boost-Dauer'],
    ['number.ev_bm', 'boost_min_power', 1400, 'W', 'Boost-Mindestleistung'], ['number.ev_rs', 'reserve_soc', 20, '%', 'Reserve-SoC'],
    ['number.ev_ms', 'max_soc', 80, '%', 'Max-SoC'], ['number.ev_c', 'consumption', 18, 'kWh/100km', 'Verbrauch'],
    ['number.ev_pv', 'pv_share', 100, '%', 'Mindest-PV-Anteil zum Start'], ['number.ev_sd', 'stop_delay', 10, 'min', 'Stopp-Verzögerung'],
    ['number.ev_pw', 'phase_switch_minutes', 20, 'min', 'Phasenwechsel-Mindestabstand'], ['number.ev_ph', 'phase_hysteresis', 350, 'W', 'Phasenwechsel-Hysterese'],
  ];
  for (const [id, key, v, u, n] of evCfg) add('ev', id, key, v, { unit_of_measurement: u, friendly_name: 'E-Auto ' + n, min: 0, max: 20000, step: 1 }, 'config');
  add('ev', 'select.ev_phase', 'phase_mode', 'auto', { options: ['auto', 'one', 'three'], friendly_name: 'E-Auto Phasen' }, 'config');
  // 4 Heizstab – Auto
  devices.hs = { name: 'Heizstab', via_device_id: 'hub' };
  add('hs', 'sensor.hs_status', 'status', 'waiting', {icon:'mdi:water-boiler',...common(4, { geraetetyp: 'heater', status_code: 'waiting',
    reason: 'Warmwasser 47,5 °C – Start ab 2000 W Überschuss', aktuell_w: 230, mittel_w: 190, benoetigt_w: 2000 })});
  add('hs', 'sensor.hs_power', 'power', 0, { unit_of_measurement: 'W' });
  add('hs', 'select.hs_mode', 'mode', 'auto', modeOpts);
  // 5 Poolpumpe
  devices.pool = { name: 'Poolpumpe', via_device_id: 'hub' };
  add('pool', 'sensor.pool_status', 'status', 'running', {icon:'mdi:pool',...common(5, { geraetetyp: 'pool', status_code: 'running',
    reason: 'Laufzeit heute 2,5 von 6,0 h', aktuell_w: 230, mittel_w: 190, benoetigt_w: 650 })});
  add('pool', 'sensor.pool_power', 'power', 640, { unit_of_measurement: 'W' });
  add('pool', 'select.pool_mode', 'mode', 'auto', modeOpts);
  return { entities, states, devices };
}

(async () => {
  const browser = await chromium.launch();
  const shoot = async (name, width, config, actions = async () => {}, clip) => {
    const p = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 2, timezoneId: 'Europe/Vienna', locale: 'de-AT' });
    await p.clock.install({ time: new Date(NOW) });
    const errs = [];
    p.on('pageerror', e => errs.push(e.message));
    await p.route('http://sep.local/**', route => {
      const u = new URL(route.request().url());
      if (u.pathname === '/') return route.fulfill({ contentType: 'text/html', body: page });
      if (u.pathname.endsWith('sep-logo.png')) return route.fulfill({ contentType: 'image/png', body: logo });
      if (u.pathname.startsWith('/f/')) return route.fulfill({ contentType: 'font/woff2', body: font(u.pathname.slice(3, 6)) });
      return route.fulfill({ status: 404, body: '' });
    });
    await p.goto('http://sep.local/');
    await p.addScriptTag({ content: cardSrc, type: 'module' });
    await p.evaluate(async ({ config, data }) => {
      const c = document.createElement('smartify-energy-plan-card');
      c.setConfig(config);
      document.getElementById('wrap').appendChild(c);
      c.hass = { ...data, language: 'de', locale: { language: 'de' }, callService: () => Promise.resolve() };
      await document.fonts.ready;
    }, { config, data: scenario(NOW) });
    await p.waitForTimeout(300);
    await actions(p);
    await p.waitForTimeout(200);
    const el = await p.$('#wrap');
    await el.screenshot({ path: path.join(out, name) });
    if (errs.length) console.log(name, errs);
    await p.close();
  };
  const root = sel => `document.querySelector('smartify-energy-plan-card').shadowRoot.querySelector('${sel}')`;
  await shoot('sep-card-desktop.png', 1000, { title: 'Energiemanager', show_timeline: true });
  await shoot('sep-card-mobile.png', 412, { title: 'Energiemanager', show_timeline: false });
  await shoot('sep-settings.png', 820, { title: 'Energiemanager', show_timeline: false, show_header: false }, async p => {
    await p.evaluate(`${root('[data-gear="ev"]')}.click()`);
    await p.evaluate(`${root('[data-info="ev:number.ev_ms"]')}.click()`);
    await p.evaluate(`(() => { const r = document.querySelector('smartify-energy-plan-card').shadowRoot;
      const s = r.querySelector('.settings'); const dev = s.closest('.devwrap') || s.parentElement;
      r.querySelectorAll('.dev, .devwrap, .settings').forEach(x => x.dataset.keep = '');
    })()`);
  });
  await shoot('sep-diagnose.png', 820, { title: 'Energiemanager', show_timeline: false, show_header: false }, async p => {
    await p.evaluate(`${root('[data-log="wm"]')}.click()`);
  });
  await browser.close();
})();
