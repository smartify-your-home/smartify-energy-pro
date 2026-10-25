/**
 * smartify-energy-plan-card
 * Lovelace Custom Card für den smartify Energiemanager (Integration smartify_energy).
 * Zeigt Überschuss, Prioritäten (Drag & Drop) und den PV-Plan der nächsten Stunden.
 * Version: 1.1.0
 *
 * Installation: /config/www/smartify-energy-plan-card.js
 * Resource:     /local/smartify-energy-plan-card.js  (type: module)
 *
 * YAML (alles optional – Hub und Geräte werden automatisch gefunden):
 *   type: custom:smartify-energy-plan-card
 *   title: Energiemanager
 *   hub: <device_id>          # nur nötig bei mehreren Energiemanagern
 *   show_header: true
 *   show_priorities: true
 *   show_timeline: true
 *   timeline_hours: 24
 *   show_mode: true           # Modus-Auswahl je Gerät
 *   show_settings: true       # Zahnrad: alle Einstellungen je Gerät / Energiemanager
 *
 * Theme-Variablen (haben Vorrang):
 *   smartify-plan-row-background   Zeilen-/Kachelhintergrund (default card-background-color)
 *   smartify-plan-border-radius    Eckenradius (default 6px)
 *   smartify-plan-text-color       Textfarbe (default primary-text-color)
 */

const CARD_VERSION = "1.1.0";
const DOMAIN = "smartify_energy";

const PALETTE = [
  ["#80DEEA", "#00ACC1"],
  ["#4FC3F7", "#0288D1"],
  ["#81C784", "#2E7D32"],
  ["#CE93D8", "#8E24AA"],
  ["#FFF59D", "#FF9800"],
  ["#F48FB1", "#C2185B"],
  ["#B0BEC5", "#546E7A"],
  ["#A5D6A7", "#00897B"],
];
const PV_GRADIENT = ["#ff9900", "#ffc34d"];
const FORCED_GRADIENT = ["#FFB74D", "#E65100"];
const BATTERY_GRADIENT = ["#9FA8DA", "#3949AB"];

const OPTION_LABELS = {
  auto: "Automatik", observe: "Beobachten", manual: "Manuell", off: "Aus",
  forecast: "Prognose", battery_first: "Speicher zuerst", devices_first: "Geräte zuerst",
  summer: "Sommer", winter: "Winter",
  pv_only: "Nur PV", km_until: "km bis Uhrzeit", days: "Tage-Konfigurator", now: "Sofort laden",
  one: "1-phasig", three: "3-phasig",
};
const MODE_LABELS = { auto: "Automatik", observe: "Beobachten", manual: "Manuell", off: "Aus" };
const TYPE_ICONS = { load: "mdi:washing-machine", pool: "mdi:pool", ev: "mdi:ev-station", heatpump: "mdi:heat-pump" };
const STATUS_LABELS = {
  laeuft: "läuft", wartet: "wartet", bereit: "bereit", erkannt: "erkannt", fertig: "fertig",
  aus: "aus", manuell: "manuell", beobachten: "beobachten", inaktiv: "inaktiv", sperrzeit: "Sperrzeit",
  max_erreicht: "Max erreicht", nicht_verbunden: "nicht angesteckt", voll: "voll",
  laedt_pv: "lädt PV", laedt_pflicht: "lädt (Ziel)", laedt_sofort: "lädt sofort", boost: "Boost",
};

const SETTING_DOMAINS = ["select", "switch", "time", "number", "button"];

const esc = s => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const grad = g => `linear-gradient(to right,${g.join(",")})`;
const num = v => { const n = parseFloat(v); return isNaN(n) ? null : n; };
const fmtW = w => (w == null ? "–" : Math.abs(w) >= 10000 ? `${(w / 1000).toFixed(1)} kW` : `${Math.round(w)} W`);
const fmtTime = iso => {
  const d = new Date(iso);
  if (isNaN(d)) return null;
  const today = new Date();
  const t = d.toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" });
  return d.toDateString() === today.toDateString() ? t : `${d.toLocaleDateString("de-AT", { weekday: "short" })} ${t}`;
};

// ── Auto-Erkennung über Entity-/Device-Registry ─────────────────────────────

function findHubs(hass) {
  const hubs = new Map();
  for (const e of Object.values(hass?.entities || {})) {
    if (e.platform !== DOMAIN || e.translation_key !== "plan" || !e.device_id) continue;
    const dev = hass.devices?.[e.device_id];
    hubs.set(e.device_id, dev?.name_by_user || dev?.name || "Energiemanager");
  }
  return hubs;
}

function collect(hass, hubId) {
  const byDevice = {};
  const settings = {};
  for (const e of Object.values(hass?.entities || {})) {
    if (e.platform !== DOMAIN || !e.device_id) continue;
    (byDevice[e.device_id] ||= {})[`${e.entity_id.split(".")[0]}:${e.translation_key}`] = e.entity_id;
    const dom = e.entity_id.split(".")[0];
    if (SETTING_DOMAINS.includes(dom) && !["priority"].includes(e.translation_key)
        && !(dom === "select" && e.translation_key === "mode")) {
      (settings[e.device_id] ||= []).push({ id: e.entity_id, dom, key: e.translation_key, config: e.entity_category === "config" });
    }
  }
  for (const list of Object.values(settings)) {
    list.sort((a, b) => (a.config - b.config) || (SETTING_DOMAINS.indexOf(a.dom) - SETTING_DOMAINS.indexOf(b.dom)));
  }
  const hubs = findHubs(hass);
  const hub = hubId && hubs.has(hubId) ? hubId : [...hubs.keys()][0];
  if (!hub) return null;
  const devices = Object.entries(byDevice)
    .filter(([id]) => id !== hub && hass.devices?.[id]?.via_device_id === hub)
    .map(([id, ents]) => {
      const dev = hass.devices[id];
      return {
        id,
        name: dev?.name_by_user || dev?.name || id,
        status: ents["sensor:status"],
        power: ents["sensor:power"],
        planned: ents["sensor:planned_start"],
        priority: ents["number:priority"],
        mode: ents["select:mode"],
        active: ents["binary_sensor:active"],
        settings: settings[id] || [],
      };
    })
    .filter(d => d.status && d.priority);
  devices.sort((a, b) => a.id.localeCompare(b.id));
  devices.forEach((d, i) => { d.color = PALETTE[i % PALETTE.length]; });
  return { hub, name: hubs.get(hub), ents: byDevice[hub] || {}, devices, hubSettings: settings[hub] || [] };
}

// ── Editor ──────────────────────────────────────────────────────────────────

const EDITOR_CSS = `
  :host { display:block; font-family:var(--primary-font-family,sans-serif); color:var(--primary-text-color); }
  .section { font-size:11px; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
    color:var(--secondary-text-color); border-bottom:1px solid var(--divider-color);
    padding-bottom:4px; margin:14px 0 8px; }
  label { font-size:12px; color:var(--secondary-text-color); display:block; margin:6px 0 2px; }
  input[type=text], input[type=number], select { width:100%; box-sizing:border-box;
    background:var(--card-background-color); color:var(--primary-text-color);
    border:1px solid var(--divider-color); border-radius:4px; padding:6px 8px; font-size:13px; }
  .row { display:flex; gap:8px; align-items:center; margin:6px 0; }
  .row label { margin:0; font-size:13px; color:var(--primary-text-color); }
  input[type=checkbox] { width:16px; height:16px; cursor:pointer; flex-shrink:0; }
  .hint { font-size:11px; color:var(--secondary-text-color); margin-top:3px; }
`;

class SmartifyEnergyPlanCardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._config = {}; }
  set hass(h) { const first = !this._hass; this._hass = h; if (first) this._render(); }
  setConfig(config) { this._config = { ...config }; this._render(); }

  _emit() {
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
  }

  _render() {
    const c = this._config;
    const hubs = this._hass ? findHubs(this._hass) : new Map();
    const chk = (k, d = true) => (c[k] ?? d) ? "checked" : "";
    this.shadowRoot.innerHTML = `
      <style>${EDITOR_CSS}</style>
      <div class="section">Allgemein</div>
      <label>Titel</label>
      <input type="text" id="title" value="${esc(c.title ?? "")}" placeholder="Name des Energiemanagers">
      <label>Energiemanager</label>
      <select id="hub">
        <option value="">Automatisch (erster gefundener)</option>
        ${[...hubs].map(([id, name]) => `<option value="${id}" ${c.hub === id ? "selected" : ""}>${esc(name)}</option>`).join("")}
      </select>
      ${hubs.size ? "" : `<div class="hint">Kein smartify Energiemanager gefunden – Integration installiert?</div>`}
      <div class="section">Bereiche</div>
      <div class="row"><input type="checkbox" id="show_header" ${chk("show_header")}><label for="show_header">Überschuss-Leiste</label></div>
      <div class="row"><input type="checkbox" id="show_priorities" ${chk("show_priorities")}><label for="show_priorities">Prioritäten (Drag &amp; Drop)</label></div>
      <div class="row"><input type="checkbox" id="show_mode" ${chk("show_mode")}><label for="show_mode">Modus-Auswahl je Gerät</label></div>
      <div class="row"><input type="checkbox" id="show_settings" ${chk("show_settings")}><label for="show_settings">Einstellungen (Zahnrad) erlauben</label></div>
      <div class="row"><input type="checkbox" id="show_timeline" ${chk("show_timeline")}><label for="show_timeline">PV-Plan (Zeitleiste)</label></div>
      <label>Zeitleiste – Stunden</label>
      <input type="number" id="timeline_hours" min="6" max="36" value="${c.timeline_hours ?? 24}">
    `;
    const set = (k, v) => { this._config = { ...this._config, [k]: v }; if (v === "" || v == null) delete this._config[k]; this._emit(); };
    const $ = id => this.shadowRoot.getElementById(id);
    $("title").addEventListener("change", e => set("title", e.target.value));
    $("hub").addEventListener("change", e => set("hub", e.target.value));
    ["show_header", "show_priorities", "show_mode", "show_settings", "show_timeline"].forEach(k =>
      $(k).addEventListener("change", e => set(k, e.target.checked)));
    $("timeline_hours").addEventListener("change", e => set("timeline_hours", parseInt(e.target.value) || 24));
  }
}
customElements.define("smartify-energy-plan-card-editor", SmartifyEnergyPlanCardEditor);

// ── Card ────────────────────────────────────────────────────────────────────

const CARD_CSS = `
  :host { display:block; --row-bg:var(--smartify-plan-row-background, var(--card-background-color));
          --radius:var(--smartify-plan-border-radius, 6px); --txt:var(--smartify-plan-text-color, var(--primary-text-color)); }
  ha-card { padding:12px; color:var(--txt); }
  .title { font-size:16px; font-weight:600; margin:0 0 10px 2px; display:flex; align-items:center; gap:8px; }
  .title .sp { flex:1; }
  .section { font-size:11px; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
             color:var(--secondary-text-color); margin:14px 2px 6px; display:flex; justify-content:space-between; }
  .section span:last-child { text-transform:none; letter-spacing:0; font-weight:400; }

  .tiles { display:flex; gap:4px; }
  .tile { flex:1 1 0; min-width:0; container-type:inline-size; background:var(--row-bg); border-radius:var(--radius); padding:8px 4px 6px;
          display:flex; flex-direction:column; align-items:center; cursor:pointer; box-sizing:border-box;
          border-style:solid; border-width:0 0 4px 0; border-image-slice:1; box-shadow:var(--ha-card-box-shadow,none); }
  .tile ha-icon { --mdc-icon-size:22px; }
  .tile .v { font-weight:bold; font-size:min(17px, 21cqw); margin-top:2px; white-space:nowrap; }
  .tile .n { font-size:min(11px, 16cqw); opacity:.75; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:100%; }

  select.mode { appearance:none; -webkit-appearance:none; border:1px solid var(--divider-color); border-radius:12px;
                background:var(--secondary-background-color); color:var(--txt); font-size:11px;
                padding:3px 10px; cursor:pointer; max-width:110px; }
  select.mode.auto { border-color:#43A047; } select.mode.observe { border-color:#0288D1; }
  select.mode.off { border-color:#E65100; }

  .list { display:flex; flex-direction:column; gap:4px; position:relative; }
  .dev { display:grid; grid-template-columns:22px 26px 28px 1fr auto; align-items:center; gap:8px;
         background:var(--row-bg); border-radius:var(--radius); padding:8px 8px 8px 4px; box-sizing:border-box;
         border-style:solid; border-width:0 0 4px 0; border-image-slice:1; position:relative;
         transition:transform .18s ease; user-select:none; }
  .dev-wrap { transition:transform .18s ease; }
  .dev-wrap.dragging { transition:none; z-index:5; position:relative; }
  .dev-wrap.dragging .dev { box-shadow:0 8px 24px rgba(0,0,0,.35); }
  .dev.dragging { transition:none; z-index:5; box-shadow:0 8px 24px rgba(0,0,0,.35); opacity:.95; }
  .handle { cursor:grab; color:var(--secondary-text-color); font-size:18px; text-align:center; touch-action:none; }
  .handle:active { cursor:grabbing; }
  .badge { width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center;
           font-size:12px; font-weight:700; color:#000; }
  .dev ha-icon { --mdc-icon-size:24px; cursor:pointer; }
  .main { min-width:0; cursor:pointer; }
  .main .name { font-size:14px; font-weight:500; display:flex; flex-wrap:wrap; align-items:center; gap:2px 6px; }
  .main .name span.t { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; }
  .main .sub { font-size:11px; color:var(--secondary-text-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .main .plan { font-size:11px; color:var(--secondary-text-color); }
  .right { display:flex; flex-direction:column; align-items:flex-end; gap:4px; }
  .pw { font-size:13px; font-weight:bold; white-space:nowrap; }
  .chip { font-size:10px; padding:1px 6px; border-radius:8px; color:#000; font-weight:600; }

  .timeline { background:var(--row-bg); border-radius:var(--radius); padding:8px 6px 4px; box-sizing:border-box; }
  .bars { display:flex; align-items:flex-end; gap:2px; height:96px; position:relative; }
  .col { flex:1 1 0; min-width:0; height:100%; position:relative; display:flex; flex-direction:column; justify-content:flex-end; }
  .col .pv { position:absolute; left:0; right:0; bottom:0; border-radius:3px 3px 0 0; opacity:.22; background:${grad(PV_GRADIENT).replace("to right", "to top")}; }
  .col .seg { position:relative; width:100%; }
  .col .seg:last-child { border-radius:3px 3px 0 0; }
  .col.gap { margin-left:8px; }
  .col.gap::before { content:""; position:absolute; left:-6px; top:20%; bottom:0; border-left:1px dotted var(--divider-color); }
  .col.now::after { content:""; position:absolute; top:-2px; bottom:0; left:-1px; border-left:2px dashed var(--primary-color); }
  .labels { display:flex; gap:2px; margin-top:3px; }
  .labels div { flex:1 1 0; min-width:0; font-size:10px; color:var(--secondary-text-color); text-align:center; white-space:nowrap; }
  .legend { display:flex; flex-wrap:wrap; gap:4px 10px; margin-top:6px; font-size:11px; color:var(--secondary-text-color); }
  .legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:4px; vertical-align:-1px; }
  .next { font-size:12px; margin:6px 2px 0; color:var(--secondary-text-color); }
  .empty { font-size:13px; color:var(--secondary-text-color); padding:12px; text-align:center; }
  .gear { background:none; border:none; color:var(--secondary-text-color); cursor:pointer; padding:2px;
          display:flex; align-items:center; justify-content:center; border-radius:50%; }
  .gear:hover { color:var(--primary-color); }
  .gear.open { color:var(--primary-color); }
  .gear ha-icon { --mdc-icon-size:20px; }
  .dev-wrap { display:flex; flex-direction:column; }
  .settings { background:var(--secondary-background-color); border-radius:0 0 var(--radius) var(--radius);
              margin:-4px 0 0; padding:8px 10px 10px; display:grid; grid-template-columns:1fr auto; gap:6px 10px;
              align-items:center; font-size:13px; }
  .settings.hub { border-radius:var(--radius); margin:0 0 10px; }
  .settings .grp { grid-column:1 / -1; font-size:10px; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
                   color:var(--secondary-text-color); margin-top:4px; }
  .settings label { color:var(--txt); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .settings .ctl { display:flex; align-items:center; gap:4px; justify-self:end; }
  .settings input[type=number], .settings input[type=time], .settings select.set {
    background:var(--card-background-color); color:var(--txt); border:1px solid var(--divider-color);
    border-radius:4px; padding:4px 6px; font-size:13px; box-sizing:border-box; }
  .settings input[type=number] { width:80px; text-align:right; }
  .settings select.set { max-width:170px; }
  .settings .unit { font-size:11px; color:var(--secondary-text-color); min-width:30px; }
  .settings button.act { border:1px solid var(--divider-color); background:var(--card-background-color); color:var(--txt);
                         border-radius:12px; padding:3px 12px; font-size:12px; cursor:pointer; }
  .settings button.act:hover { border-color:var(--primary-color); }
  .tgl { position:relative; width:36px; height:20px; }
  .tgl input { opacity:0; width:0; height:0; }
  .tgl span { position:absolute; inset:0; background:var(--divider-color); border-radius:10px; cursor:pointer; transition:.2s; }
  .tgl span::before { content:""; position:absolute; width:16px; height:16px; left:2px; top:2px; background:#fff; border-radius:50%; transition:.2s; }
  .tgl input:checked + span { background:var(--primary-color); }
  .tgl input:checked + span::before { transform:translateX(16px); }
`;

class SmartifyEnergyPlanCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._sig = "";
    this._drag = null;
    this._open = new Set();
  }

  static getConfigElement() { return document.createElement("smartify-energy-plan-card-editor"); }
  static getStubConfig() { return { show_header: true, show_priorities: true, show_timeline: true, timeline_hours: 24 }; }

  setConfig(config) {
    this._config = { show_header: true, show_priorities: true, show_timeline: true, show_mode: true, timeline_hours: 24, ...config };
    this._sig = "";
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._drag) return;
    const data = collect(hass, this._config.hub);
    const ids = data ? [...Object.values(data.ents), ...data.hubSettings.map(x => x.id),
      ...data.devices.flatMap(d => [d.status, d.power, d.planned, d.priority, d.mode, d.active, ...d.settings.map(x => x.id)])] : [];
    const sig = ids.map(id => { const s = hass.states[id]; return s ? `${id}:${s.last_updated}` : id; }).join("|");
    if (sig === this._sig) return;
    this._data = data;
    // Nicht neu zeichnen, während ein Eingabefeld bearbeitet wird
    const active = this.shadowRoot.activeElement;
    if (active && active.matches?.("input[type=number], input[type=time]")) {
      if (!this._pendingBlur) {
        this._pendingBlur = true;
        active.addEventListener("blur", () => { this._pendingBlur = false; this._sig = ""; this.hass = this._hass; }, { once: true });
      }
      return;
    }
    this._sig = sig;
    this._render();
  }

  getCardSize() { return 3 + (this._data?.devices.length || 0); }
  getGridOptions() { return { columns: 12, min_columns: 6 }; }

  _st(id) { return id ? this._hass.states[id] : undefined; }
  _moreInfo(entityId) {
    if (!entityId) return;
    const ev = new Event("hass-more-info", { bubbles: true, composed: true });
    ev.detail = { entityId };
    this.dispatchEvent(ev);
  }

  // ── Bereiche ──────────────────────────────────────────────────────────────
  _header(d) {
    const e = d.ents;
    const surplus = this._st(e["sensor:surplus"]);
    const avg = this._st(e["sensor:surplus_avg"]);
    const alloc = this._st(e["sensor:allocated"]);
    const fc = this._st(e["sensor:forecast_today"]);
    const bat = this._st(e["sensor:battery_priority"]);
    const s = num(surplus?.state);
    const tiles = [
      { ent: e["sensor:surplus"], icon: "mdi:solar-power-variant", v: fmtW(s), n: "Überschuss", g: s > 0 ? ["#81C784", "#00ACC1"] : ["#FFB74D", "#E65100"] },
      { ent: e["sensor:surplus_avg"], icon: "mdi:chart-bell-curve", v: fmtW(num(avg?.state)), n: "Ø Überschuss", g: ["#B0BEC5", "#546E7A"] },
      { ent: e["sensor:allocated"], icon: "mdi:call-split", v: fmtW(num(alloc?.state)), n: "Verteilt", g: PALETTE[0] },
    ];
    if (fc && fc.state !== "unknown" && fc.state !== "unavailable") {
      const rest = fc.attributes.rest_heute_kwh;
      tiles.push({ ent: e["sensor:forecast_today"], icon: "mdi:weather-sunny", v: `${num(fc.state)?.toFixed(1)} kWh`,
                   n: rest != null ? `Rest ${Number(rest).toFixed(1)} kWh` : "Prognose heute", g: PV_GRADIENT });
    }
    if (bat) {
      tiles.push({ ent: e["sensor:battery_priority"], icon: bat.state === "speicher" ? "mdi:home-battery" : "mdi:home-lightning-bolt",
                   v: bat.state === "speicher" ? "Speicher" : "Geräte", n: "Vorrang", g: BATTERY_GRADIENT });
    }
    return `<div class="tiles">${tiles.map(t => `
      <div class="tile" data-more="${t.ent || ""}" style="border-image-source:${grad(t.g)}">
        <ha-icon icon="${t.icon}"></ha-icon><div class="v">${esc(t.v)}</div><div class="n">${esc(t.n)}</div>
      </div>`).join("")}</div>`;
  }

  _modeSelect(entityId, cls = "") {
    const st = this._st(entityId);
    if (!st) return "";
    const opts = st.attributes.options || Object.keys(MODE_LABELS);
    return `<select class="mode ${esc(st.state)} ${cls}" data-select="${entityId}">
      ${opts.map(o => `<option value="${esc(o)}" ${o === st.state ? "selected" : ""}>${esc(MODE_LABELS[o] || o)}</option>`).join("")}
    </select>`;
  }

  _label(entityId, prefix) {
    const st = this._st(entityId);
    let name = st?.attributes?.friendly_name || entityId;
    if (prefix && name.startsWith(prefix)) name = name.slice(prefix.length).trim();
    return name;
  }

  _control(item) {
    const st = this._st(item.id);
    if (!st) return "";
    const a = st.attributes || {};
    const dis = ["unavailable", "unknown"].includes(st.state) && item.dom !== "button" ? "disabled" : "";
    switch (item.dom) {
      case "number": {
        const unit = a.unit_of_measurement ? `<span class="unit">${esc(a.unit_of_measurement)}</span>` : "";
        return `<input type="number" data-num="${item.id}" value="${esc(st.state)}" min="${a.min ?? ""}" max="${a.max ?? ""}" step="${a.step ?? "any"}" ${dis}>${unit}`;
      }
      case "select":
        return `<select class="set" data-select="${item.id}" ${dis}>${(a.options || []).map(o =>
          `<option value="${esc(o)}" ${o === st.state ? "selected" : ""}>${esc(OPTION_LABELS[o] || o)}</option>`).join("")}</select>`;
      case "switch":
        return `<label class="tgl"><input type="checkbox" data-switch="${item.id}" ${st.state === "on" ? "checked" : ""} ${dis}><span></span></label>`;
      case "time":
        return `<input type="time" data-time="${item.id}" value="${esc(String(st.state).slice(0, 5))}" ${dis}>`;
      case "button":
        return `<button class="act" data-press="${item.id}">Ausführen</button>`;
      default:
        return "";
    }
  }

  _settings(items, prefix, cls = "") {
    if (!items.length) return "";
    const main = items.filter(i => !i.config);
    const cfg = items.filter(i => i.config);
    const rows = list => list.map(i => `
      <label title="${esc(this._label(i.id, prefix))}">${esc(this._label(i.id, prefix))}</label>
      <div class="ctl">${this._control(i)}</div>`).join("");
    return `<div class="settings ${cls}">
      ${main.length ? `<div class="grp">Bedienung</div>${rows(main)}` : ""}
      ${cfg.length ? `<div class="grp">Einstellungen</div>${rows(cfg)}` : ""}
    </div>`;
  }

  _devices(d) {
    const rows = d.devices
      .map(dev => ({ dev, prio: num(this._st(dev.priority)?.state) ?? 99 }))
      .sort((a, b) => a.prio - b.prio || a.dev.name.localeCompare(b.dev.name));
    if (!rows.length) return `<div class="empty">Noch keine Geräte – in der Integration „+ Gerät hinzufügen“.</div>`;
    return `<div class="list">${rows.map(({ dev, prio }) => {
      const st = this._st(dev.status);
      const a = st?.attributes || {};
      const mode = a.modus || this._st(dev.mode)?.state;
      const reserved = num(a.reserviert_w) || 0;
      const on = reserved > 0;
      const forced = on && a.pflicht;
      const power = num(this._st(dev.power)?.state);
      const icon = a.icon || TYPE_ICONS[a.geraetetyp] || "mdi:flash";
      const border = forced ? FORCED_GRADIENT : on ? dev.color : null;
      const statusTxt = STATUS_LABELS[st?.state] || st?.state || "";
      const sub = mode === "observe" && a.empfehlung ? `Empfehlung: ${a.empfehlung}` : (a.grund || statusTxt);
      const planned = this._st(dev.planned);
      const pt = planned && planned.state && !["unknown", "unavailable"].includes(planned.state) ? fmtTime(planned.state) : null;
      const planTxt = pt ? `Empf. Start ${pt}${planned.attributes.pv_anteil_prozent != null ? ` · ${planned.attributes.pv_anteil_prozent} % PV` : ""}` : "";
      const chip = forced ? `<span class="chip" style="background:${grad(FORCED_GRADIENT)}">Pflicht</span>`
                 : on ? `<span class="chip" style="background:${grad(dev.color)}">${esc(statusTxt || "ein")}</span>`
                 : mode === "observe" ? `<span class="chip" style="background:#B3E5FC">beobachten</span>` : "";
      const open = this._open.has(dev.id);
      return `
        <div class="dev-wrap" data-wrap="${dev.id}">
        <div class="dev" data-dev="${dev.id}" style="${border ? `border-image-source:${grad(border)}` : "border-image-source:linear-gradient(var(--divider-color),var(--divider-color))"}">
          <div class="handle" title="Halten und ziehen, um die Priorität zu ändern">⠿</div>
          <div class="badge" style="background:${grad(dev.color)}">${prio === 99 ? "?" : Math.round(prio)}</div>
          <ha-icon icon="${esc(icon)}" data-more="${dev.status}" style="color:${on ? dev.color[1] : "var(--secondary-text-color)"}"></ha-icon>
          <div class="main" data-more="${dev.status}">
            <div class="name"><span class="t">${esc(dev.name)}</span>${chip}</div>
            <div class="sub" title="${esc(sub)}">${esc(sub)}</div>
            ${planTxt ? `<div class="plan">${esc(planTxt)}</div>` : ""}
          </div>
          <div class="right">
            <div style="display:flex;align-items:center;gap:4px">
              <div class="pw">${power != null && power > 0 ? fmtW(power) : ""}</div>
              ${this._config.show_settings !== false && dev.settings.length ? `<button class="gear ${open ? "open" : ""}" data-gear="${dev.id}" title="Einstellungen"><ha-icon icon="mdi:cog"></ha-icon></button>` : ""}
            </div>
            ${this._config.show_mode ? this._modeSelect(dev.mode) : ""}
          </div>
        </div>
        ${open ? this._settings(dev.settings, dev.name) : ""}
        </div>`;
    }).join("")}</div>`;
  }

  _timeline(d) {
    const plan = this._st(d.ents["sensor:plan"]);
    const hours = (plan?.attributes?.stunden || []).slice();
    if (!hours.length) return `<div class="timeline"><div class="empty">Keine Prognose verfügbar.</div></div>`;
    const now = Date.now();
    const horizon = now + (this._config.timeline_hours || 24) * 3600e3;
    const cols = hours.filter(h => { const t = Date.parse(h.zeit); return t + 3600e3 > now && t < horizon; });
    if (!cols.length) return `<div class="timeline"><div class="empty">Kein PV-Ertrag im Zeitraum.</div></div>`;
    const colorOf = name => name === "Speicher" ? BATTERY_GRADIENT : (d.devices.find(x => x.name === name)?.color || PALETTE[6]);
    const max = Math.max(...cols.map(h => Math.max(h.pv_w || 0, Object.values(h.geraete || {}).reduce((a, b) => a + b, 0))), 1);
    const used = new Set();
    const bars = cols.map((h, i) => {
      const t = Date.parse(h.zeit);
      const gap = i > 0 && t - Date.parse(cols[i - 1].zeit) > 3600e3;
      const isNow = t <= now && now < t + 3600e3;
      const segs = Object.entries(h.geraete || {}).map(([name, w]) => {
        used.add(name);
        const g = colorOf(name);
        return `<div class="seg" title="${esc(name)}: ${fmtW(w)}" style="height:${(w / max) * 100}%;background:linear-gradient(to top,${g.join(",")})"></div>`;
      }).join("");
      const label = new Date(t).toLocaleTimeString("de-AT", { hour: "2-digit" });
      return `<div class="col ${isNow ? "now" : ""} ${gap ? "gap" : ""}" title="${label} Uhr – PV ${fmtW(h.pv_w)}, frei ${fmtW(h.frei_w)}">
          <div class="pv" style="height:${((h.pv_w || 0) / max) * 100}%"></div>${segs}</div>`;
    }).join("");
    const step = cols.length > 16 ? 3 : cols.length > 8 ? 2 : 1;
    const labels = cols.map((h, i) => `<div style="${i > 0 && Date.parse(h.zeit) - Date.parse(cols[i - 1].zeit) > 3600e3 ? "margin-left:8px" : ""}">${i % step === 0 ? new Date(Date.parse(h.zeit)).getHours() : ""}</div>`).join("");
    const legend = [`<span><i style="background:${grad(PV_GRADIENT)};opacity:.5"></i>PV-Prognose</span>`]
      .concat([...used].map(n => `<span><i style="background:${grad(colorOf(n))}"></i>${esc(n)}</span>`)).join("");
    const next = plan?.state && plan.state !== "–" ? `<div class="next">Als Nächstes: ${esc(plan.state)}</div>` : "";
    return `<div class="timeline"><div class="bars">${bars}</div><div class="labels">${labels}</div>
      <div class="legend">${legend}</div></div>${next}`;
  }

  // ── Render ────────────────────────────────────────────────────────────────
  _render() {
    if (!this._hass) return;
    const c = this._config;
    const d = this._data ?? collect(this._hass, c.hub);
    if (!d) {
      this.shadowRoot.innerHTML = `<style>${CARD_CSS}</style><ha-card><div class="empty">Kein smartify Energiemanager gefunden.</div></ha-card>`;
      return;
    }
    const title = c.title ?? d.name;
    this.shadowRoot.innerHTML = `
      <style>${CARD_CSS}</style>
      <ha-card>
        ${title || d.ents["select:mode"] ? `<div class="title"><span>${esc(title || "")}</span><span class="sp"></span>${this._modeSelect(d.ents["select:mode"])}
          ${c.show_settings !== false && d.hubSettings.length ? `<button class="gear ${this._open.has("hub") ? "open" : ""}" data-gear="hub" title="Einstellungen Energiemanager"><ha-icon icon="mdi:cog"></ha-icon></button>` : ""}</div>` : ""}
        ${this._open.has("hub") ? this._settings(d.hubSettings, d.name, "hub") : ""}
        ${c.show_header ? this._header(d) : ""}
        ${c.show_priorities ? `<div class="section"><span>Prioritäten</span><span>ziehen zum Sortieren</span></div>${this._devices(d)}` : ""}
        ${c.show_timeline ? `<div class="section"><span>PV-Plan</span><span>${c.timeline_hours || 24} h</span></div>${this._timeline(d)}` : ""}
      </ha-card>`;
    this._bind(d);
  }

  _bind(d) {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-more]").forEach(el =>
      el.addEventListener("click", () => this._moreInfo(el.dataset.more)));
    root.querySelectorAll("select[data-select]").forEach(el => {
      el.addEventListener("click", e => e.stopPropagation());
      el.addEventListener("change", e => {
        const [domain] = el.dataset.select.split(".");
        this._hass.callService(domain, "select_option", { entity_id: el.dataset.select, option: e.target.value });
      });
    });
    root.querySelectorAll(".handle").forEach(h => h.addEventListener("pointerdown", e => this._dragStart(e, d)));
    root.querySelectorAll("[data-gear]").forEach(el => el.addEventListener("click", e => {
      e.stopPropagation();
      const id = el.dataset.gear;
      this._open.has(id) ? this._open.delete(id) : this._open.add(id);
      this._render();
    }));
    root.querySelectorAll("input[data-num]").forEach(el => el.addEventListener("change", e => {
      const v = parseFloat(e.target.value);
      if (!isNaN(v)) this._hass.callService("number", "set_value", { entity_id: el.dataset.num, value: v });
    }));
    root.querySelectorAll("input[data-switch]").forEach(el => el.addEventListener("change", e =>
      this._hass.callService("switch", e.target.checked ? "turn_on" : "turn_off", { entity_id: el.dataset.switch })));
    root.querySelectorAll("input[data-time]").forEach(el => el.addEventListener("change", e => {
      if (e.target.value) this._hass.callService("time", "set_value", { entity_id: el.dataset.time, time: `${e.target.value}:00` });
    }));
    root.querySelectorAll("button[data-press]").forEach(el => el.addEventListener("click", e => {
      e.stopPropagation();
      this._hass.callService("button", "press", { entity_id: el.dataset.press });
    }));
  }

  // ── Drag & Drop (Maus + Touch, ohne externe Bibliothek) ──────────────────
  _dragStart(e, d) {
    const row = e.target.closest(".dev-wrap");
    const list = row?.parentElement;
    if (!row || !list) return;
    e.preventDefault();
    const rows = [...list.querySelectorAll(":scope > .dev-wrap")];
    const rects = rows.map(r => r.getBoundingClientRect());
    const from = rows.indexOf(row);
    const step = rows.length > 1 ? Math.min(...rects.slice(1).map((r, i) => r.top - rects[i].top)) : rects[0].height + 4;
    this._drag = { row, rows, rects, from, to: from, startY: e.clientY, step, d };
    row.classList.add("dragging");
    row.setPointerCapture?.(e.pointerId);
    const move = ev => this._dragMove(ev);
    const end = ev => {
      row.removeEventListener("pointermove", move);
      row.removeEventListener("pointerup", end);
      row.removeEventListener("pointercancel", end);
      this._dragEnd(ev);
    };
    row.addEventListener("pointermove", move);
    row.addEventListener("pointerup", end);
    row.addEventListener("pointercancel", end);
  }

  _dragMove(e) {
    const g = this._drag;
    if (!g) return;
    const dy = e.clientY - g.startY;
    g.row.style.transform = `translateY(${dy}px)`;
    const to = Math.max(0, Math.min(g.rows.length - 1, g.from + Math.round(dy / g.step)));
    g.to = to;
    g.rows.forEach((r, i) => {
      if (r === g.row) return;
      let shift = 0;
      if (g.from < to && i > g.from && i <= to) shift = -g.step;
      if (g.from > to && i < g.from && i >= to) shift = g.step;
      r.style.transform = shift ? `translateY(${shift}px)` : "";
    });
  }

  async _dragEnd() {
    const g = this._drag;
    if (!g) return;
    const order = g.rows.map(r => r.dataset.wrap);
    const [moved] = order.splice(g.from, 1);
    order.splice(g.to, 0, moved);
    g.rows.forEach(r => { r.style.transform = ""; r.classList.remove("dragging"); });
    this._drag = null;
    if (g.to !== g.from) {
      const calls = order.map((id, idx) => {
        const dev = g.d.devices.find(x => x.id === id);
        const prio = Math.min(idx + 1, 10);
        const cur = num(this._st(dev?.priority)?.state);
        return dev && cur !== prio
          ? this._hass.callService("number", "set_value", { entity_id: dev.priority, value: prio })
          : null;
      }).filter(Boolean);
      await Promise.all(calls);
    }
    this._sig = "";
    this.hass = this._hass;
  }
}

customElements.define("smartify-energy-plan-card", SmartifyEnergyPlanCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "smartify-energy-plan-card",
  name: "smartify Energiemanager",
  description: "Überschuss, Prioritäten (Drag & Drop) und PV-Plan des smartify Energiemanagers.",
  preview: false,
});
console.info(`%c SMARTIFY-ENERGY-PLAN-CARD %c v${CARD_VERSION} `, "background:#00ACC1;color:#fff", "background:#333;color:#fff");
