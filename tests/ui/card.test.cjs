const {test} = require('node:test');
const assert = require('node:assert/strict');
const {JSDOM} = require('jsdom');
const fs = require('node:fs');
const source=fs.readFileSync('custom_components/smartify_energy/www/smartify-energy-plan-card.js','utf8');
test('live patch preserves DOM nodes and handlers while updating numbers',()=>{
  const dom=new JSDOM('<div id="root"></div>',{runScripts:'outside-only'});
  dom.window.eval(source+'\nwindow.patchChildren=patchChildren;');
  const {document}=dom.window;
  const root=document.querySelector('#root');
  root.innerHTML='<div><span>100 W</span><select data-select="select.mode"><option value="auto">Auto</option></select></div>';
  const span=root.querySelector('span'), select=root.querySelector('select');
  let count=0;select.addEventListener('change',()=>count++);
  const tpl=document.createElement('template');
  tpl.innerHTML='<div><span>250 W</span><select data-select="select.mode"><option value="auto">Auto</option><option value="off" selected>Off</option></select></div>';
  dom.window.patchChildren(root,tpl.content);
  assert.equal(root.querySelector('span'),span);
  assert.equal(span.textContent,'250 W');
  assert.equal(root.querySelector('select'),select);
  assert.equal(select.value,'off');
  select.dispatchEvent(new dom.window.Event('change'));
  assert.equal(count,1);
});
test('patch removes stale nodes after structural changes',()=>{
  const dom=new JSDOM('<div id="root"><div>old</div><span>stale</span></div>',{runScripts:'outside-only'});
  dom.window.eval(source+'\nwindow.patchChildren=patchChildren;');
  const root=dom.window.document.querySelector('#root'),tpl=dom.window.document.createElement('template');
  tpl.innerHTML='<section>new</section>';
  dom.window.patchChildren(root,tpl.content);
  assert.equal(root.innerHTML,'<section>new</section>');
});

test('battery rank stays in priority model but not hub configuration rows',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source+'\nwindow.collectSEP=collect;');
  const hub='hub1';
  const entities={
    plan:{platform:'smartify_energy',translation_key:'plan',device_id:hub,entity_id:'sensor.sep_plan'},
    battery:{platform:'smartify_energy',translation_key:'battery_priority',device_id:hub,entity_id:'sensor.battery_priority'},
    rank:{platform:'smartify_energy',translation_key:'battery_rank',device_id:hub,entity_id:'number.battery_rank',entity_category:'config'},
    trend:{platform:'smartify_energy',translation_key:'trend_window',device_id:hub,entity_id:'number.trend_window',entity_category:'config'},
  };
  const data=dom.window.collectSEP({entities,devices:{[hub]:{name:'SEP'}},states:{}},hub);
  assert.ok(data.devices.some(d=>d.virtualBattery && d.rankEntity==='number.battery_rank'));
  assert.ok(!data.hubSettings.some(x=>x.key==='battery_rank'));
  assert.ok(data.hubSettings.some(x=>x.key==='trend_window'));
});
test('gear transition invalidates stale data and signature before rendering',()=>{
  assert.match(source,/this\._open\.has\(id\) \? this\._open\.delete\(id\) : this\._open\.add\(id\);[\s\S]*?this\._sig = "";[\s\S]*?this\._data = collect\(this\._hass, this\._config\.hub\);[\s\S]*?this\._render\(\)/);
});

test('H/T/B display is limited to load and heat pump',()=>{
  assert.match(source,/\["load", "heatpump"\]\.includes\(a\.geraetetyp\)/);
  assert.match(source,/history_avg_ready/);
  assert.match(source,/trend_ready/);
  assert.match(source,/gate\("H", avgReady, historyInfo\)/);
  assert.match(source,/gate\("T", trendOk, trendInfo\)/);
  assert.match(source,/gate\("B", budgetOk, budgetInfo\)/);
  assert.match(source,/avgReady && trendOk && budgetOk/);
});

test('short-window arrow follows the three-gate threshold and neutral rule',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source+'\nwindow.deviceTrendTest=deviceTrend;');
  const trend=dom.window.deviceTrendTest;
  assert.equal(trend(2200,2000,-500,100,true).direction,'down',
    'falling below threshold blocks despite enough current short average');
  assert.equal(trend(2400,2000,-300,100,true).allowed,true,
    'falling but projected above requirement remains allowed');
  assert.equal(trend(1900,2000,0,100,true).direction,'down');
  assert.equal(trend(1900,2000,-50,100,true).allowed,false);
  assert.equal(trend(1400,2000,50,100,true).allowed,false);
  assert.equal(trend(2200,2000,50,100,true).allowed,true);
  assert.equal(trend(1900,2000,-250,100,true).direction,'down');
  assert.equal(trend(1900,2000,-250,100,true).allowed,false);
  assert.equal(trend(1900,2000,250,100,false).direction,'pending');
  assert.equal(trend(null,2000,300,100,true).direction,'pending');
});

test('expandable H/T/B log exposes live actual and target values',()=>{
  assert.match(source,/const avgWindow = num\(this\._st\(d\.ents\["number:avg_window"\]\)\?\.state\)/);
  assert.match(source,/const historyNeed = avgWindow == null \? null : avgWindow \* 0\.9/);
  assert.match(source,/const trendHistoryNeed = trendWindow == null \? null : trendWindow \* 2/);
  assert.match(source,/logRow\("H", avgReady/);
  assert.match(source,/logRow\("T", trendOk/);
  assert.match(source,/logRow\("B", budgetOk/);
  assert.match(source,/data-log-panel/);
  assert.match(source,/data-log=/);
  assert.match(source,/this\._logOpen\.has\(id\) \? this\._logOpen\.delete\(id\) : this\._logOpen\.add\(id\)/);
  assert.match(source,/Neues Programm wird autom\. erkannt/);
  assert.doesNotMatch(source,/<div class="pb-extra">\s*<span>Ø/);
});

function settingsCard(goal='pv_only'){
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const E=(id,k,dev,cat)=>({platform:'smartify_energy',translation_key:k,device_id:dev,entity_id:id,entity_category:cat});
  const S=(state,name,extra={})=>({state,attributes:{friendly_name:name,...extra}});
  const entities={
    plan:E('sensor.plan','plan','hub'), st:E('sensor.ev','status','ev'),
    mode:E('select.ev_mode','mode','ev'), goal:E('select.ev_goal','goal','ev'),
    dl:E('time.ev_deadline','deadline','ev'), km:E('number.ev_target_km','target_km','ev'),
    boost:E('switch.ev_boost','boost','ev'), bf:E('number.ev_boost_factor','boost_factor','ev','config'),
    max:E('number.ev_max_soc','max_soc','ev','config'), sd:E('number.ev_stop_delay','stop_delay','ev','config'),
    pv:E('number.ev_pv_share','pv_share','ev','config'),
  };
  const states={'sensor.plan':S('–','Plan',{stunden:[]}),'sensor.ev':S('charging_pv','Auto',{geraetetyp:'ev',modus:'auto'}),
    'select.ev_mode':S('auto','Auto Modus',{options:['auto','observe','manual','off']}),
    'select.ev_goal':S(goal,'Auto Ladeziel',{options:['pv_only','km_until','days','now']}),
    'time.ev_deadline':S('06:00:00','Auto Fertig bis / Abfahrt'),'number.ev_target_km':S('300','Auto Ziel-Kilometer',{unit_of_measurement:'km'}),
    'switch.ev_boost':S('off','Auto PV-Boost'),'number.ev_boost_factor':S('2.5','Auto Boost-Faktor',{unit_of_measurement:'×'}),
    'number.ev_max_soc':S('100','Auto Max-SoC',{unit_of_measurement:'%'}),'number.ev_stop_delay':S('30','Auto Stopp-Verzögerung',{unit_of_measurement:'min'}),
    'number.ev_pv_share':S('100','Auto Mindest-PV-Anteil zum Start',{unit_of_measurement:'%'})};
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:false});
  dom.window.document.body.appendChild(card);
  card.hass={entities,states,devices:{hub:{name:'SEP'},ev:{name:'Auto',via_device_id:'hub'}},callService(){return Promise.resolve()}};
  card.shadowRoot.querySelector('[data-gear="ev"]').click();
  return card.shadowRoot;
}

test('settings are grouped, short by default and expand long help via (i)',()=>{
  const root=settingsCard();
  const titles=[...root.querySelectorAll('.sgh span')].map(x=>x.textContent);
  assert.deepEqual(titles,['Bedienung','PV-Boost','Fahrzeug','Erweitert']);
  assert.equal(root.querySelectorAll('.setting-help').length,0,'long help hidden by default');
  assert.ok([...root.querySelectorAll('.sshort')].some(x=>x.textContent==='Ladung endet hier'));
  const adv=[...root.querySelectorAll('.sgrp')].find(g=>g.textContent.includes('Erweitert'));
  assert.equal(adv.querySelector('.sgrid'),null,'advanced collapsed');
  assert.match(adv.querySelector('small').textContent,/Mindest-PV-Anteil zum Start 100 %/);
  root.querySelector('[data-info="ev:number.ev_max_soc"]').click();
  assert.equal(root.querySelectorAll('.setting-help').length,1);
  assert.match(root.querySelector('.setting-help').textContent,/Max|Akkustand/);
  adv.querySelector('[data-grp]').click();
  assert.ok(root.querySelector('[data-num="number.ev_stop_delay"]'),'advanced opens on click');
});

test('charge goal fields are shown only for km_until',()=>{
  assert.equal(settingsCard('pv_only').querySelector('[data-num="number.ev_target_km"]'),null);
  assert.equal(settingsCard('pv_only').querySelector('[data-time="time.ev_deadline"]'),null);
  const km=settingsCard('km_until');
  assert.ok(km.querySelector('[data-num="number.ev_target_km"]'));
  assert.ok(km.querySelector('[data-time="time.ev_deadline"]'));
});

test('every documented setting has a short text and a group',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source+'\nwindow.T={SETTING_HELP,SETTING_SHORT,SETTING_GROUPS};');
  const {SETTING_HELP,SETTING_SHORT,SETTING_GROUPS}=dom.window.T;
  const grouped=new Set(SETTING_GROUPS.flatMap(g=>g.keys));
  const keys=Object.keys(SETTING_HELP).filter(k=>!['priority'].includes(k));
  assert.deepEqual(keys.filter(k=>!SETTING_SHORT[k]),[],'missing short text');
  assert.deepEqual(keys.filter(k=>!grouped.has(k)),[],'missing group');
  for (const t of Object.values(SETTING_SHORT)) assert.ok(t.length<=34,`short text too long: ${t}`);
});

function rowCard(devs){
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const entities={plan:{platform:'smartify_energy',translation_key:'plan',device_id:'hub',entity_id:'sensor.plan'}};
  const states={'sensor.plan':{state:'-',attributes:{stunden:[]}}};
  const devices={hub:{name:'SEP'}};
  for (const [dev,list] of Object.entries(devs)) {
    devices[dev]={name:dev,via_device_id:'hub'};
    for (const [id,k,state,attrs] of list) { entities[id]={platform:'smartify_energy',translation_key:k,device_id:dev,entity_id:id}; states[id]={state,attributes:attrs||{}}; }
  }
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:false});
  dom.window.document.body.appendChild(card);
  card.hass={entities,states,devices,callService(){return Promise.resolve()}};
  return card.shadowRoot;
}

test('device rows: no mode select, EV shows charge goal, loads show actions',()=>{
  const modeOpts={options:['auto','observe','manual','off']};
  const root=rowCard({
    ev:[['sensor.ev','status','charging_pv',{geraetetyp:'ev',modus:'auto'}],['select.ev_mode','mode','auto',modeOpts],
        ['select.ev_goal','goal','pv_only',{options:['pv_only','km_until','days','now']}]],
    wm:[['sensor.wm','status','waiting',{geraetetyp:'load',modus:'auto',phase:'wartet'}],['select.wm_mode','mode','auto',modeOpts],
        ['button.wm_start','start_now','x'],['switch.wm_n','nachladen','off'],['button.wm_reset','reset','x']],
    pool:[['sensor.pool','status','off',{geraetetyp:'pool',modus:'off'}],['select.pool_mode','mode','off',modeOpts]],
  });
  assert.equal(root.querySelector('.list [data-select="select.ev_mode"]'),null,'mode moved to settings');
  assert.equal(root.querySelector('.list [data-select="select.wm_mode"]'),null);
  assert.ok(root.querySelector('.list select.quick[data-select="select.ev_goal"]'),'EV goal selectable in row');
  const wm=root.querySelector('[data-wrap="wm"]')||root;
  const labels=[...root.querySelectorAll('.sep-act')].map(b=>b.textContent.trim());
  assert.deepEqual(labels,['Sofortstart','Nachladen']);
  assert.match(root.textContent,/Aus/,'non-auto mode stays visible as tag');
  assert.ok(root.querySelector('.mode-tag.off'));
});

test('heater row offers Auto/Ein/Aus mapped to auto/manual/off',()=>{
  const calls=[];
  const root=rowCard({hs:[['sensor.hs','status','manuell',{geraetetyp:'heater',modus:'manual'}],['select.hs_mode','mode','manual',{options:['auto','observe','manual','off']}]]});
  const card=root.host; card._hass.callService=(d,s,data)=>{calls.push([d,s,data]);return Promise.resolve();};
  const btns=[...root.querySelectorAll('.seg button')];
  assert.deepEqual(btns.map(b=>b.textContent),['Auto','Ein','Aus']);
  assert.ok(btns[1].classList.contains('on'),'Ein active in manual mode');
  assert.equal(root.querySelector('.mode-tag'),null,'no duplicate mode tag');
  btns[2].click();
  assert.equal(JSON.stringify(calls[0]),JSON.stringify(['select','select_option',{entity_id:'select.hs_mode',option:'off'}]));
});

test('heater Auto/Ein/Aus shares the metrics container; narrow layout puts it above the measurements',()=>{
  const root=rowCard({hs:[
    ['sensor.hs','status','manuell',{geraetetyp:'heater',modus:'manual'}],
    ['select.hs_mode','mode','manual',{options:['auto','observe','manual','off']}],
  ]});
  const heater=root.querySelector('.heater-power-budget');
  assert.ok(heater,'heater has its own responsive metrics container');
  assert.ok(heater.classList.contains('power-budget'));
  const seg=heater.querySelector(':scope > .seg');
  const pair=heater.querySelector(':scope > .pb-pair');
  assert.ok(seg,'Auto/Ein/Aus is inside power-budget, not a sibling');
  assert.ok(pair,'power and budget stay grouped together');
  assert.ok(seg.compareDocumentPosition(pair) & 4,'switch is before power/budget for narrow stacking');
  assert.deepEqual([...seg.querySelectorAll('button')].map(b=>b.textContent),['Auto','Ein','Aus']);
  assert.equal(pair.querySelectorAll('.pb-item').length,2);
  const css=source;
  assert.match(css,/\.heater-power-budget\s*\{\s*flex-wrap:nowrap;/,'desktop uses a horizontal metrics group');
  assert.match(css,/@container \(max-width:560px\)\s*\{[\s\S]*?\.heater-power-budget\s*\{\s*flex-direction:column;/,
    'mobile card container stacks switch over both metrics');
  assert.match(css,/\.heater-power-budget \.seg\s*\{\s*align-self:flex-end;/,
    'mobile switch stays in right metrics column');
  assert.match(css,/\.right\s*\{\s*grid-column:5; grid-row:1;/,
    'mobile metrics never move below device status');
});

test('EV boost with running stop delay says "Boost endet", not "PV-Stopp"',()=>{
  const soon=new Date(Date.now()+20*60e3).toISOString();
  const root=rowCard({ev:[['sensor.ev','status','boost',{geraetetyp:'ev',modus:'auto',status_code:'boost',reason:'Boost ×2 6 A × 3',pv_stopp_um:soon,boost_bis:new Date(Date.now()+3*3600e3).toISOString()}],
    ['select.ev_goal','goal','pv_only',{options:['pv_only','km_until','days','now']}],['switch.ev_boost','boost','on']]});
  const stop=root.querySelector('.plan.sep-stop');
  assert.ok(stop);
  assert.match(stop.textContent,/Boost endet/);
  assert.doesNotMatch(root.textContent,/PV-Stopp/);
});

test('EV controls (goal + boost) sit inside the metrics block before the battery',()=>{
  const root=rowCard({ev:[['sensor.ev','status','charging_pv',{geraetetyp:'ev',modus:'auto',soc:52}],['select.ev_mode','mode','auto',{options:['auto','observe','manual','off']}],
    ['select.ev_goal','goal','pv_only',{options:['pv_only','km_until','days','now']}],['switch.ev_boost','boost','off']]});
  const pb=root.querySelector('.power-budget.ev-power-budget');
  assert.ok(pb,'EV metrics block');
  const ctl=pb.querySelector(':scope > .ev-ctl');
  assert.ok(ctl && ctl.querySelector('select.quick[data-select="select.ev_goal"]') && ctl.querySelector('button.boost'));
  assert.equal(pb.firstElementChild,ctl,'controls first, then Akku/Leistung/Budget');
  assert.match(source,/@container \(max-width:560px\)[\s\S]*\.ev-power-budget \.ev-ctl \{ width:100%/);
});

test('EV shows history + budget start check (no trend) with exact threshold in Info',()=>{
  const gateAttrs={geraetetyp:'ev',modus:'auto',status_code:'waiting',trend_history_min:3,
    pv_startpruefung:{schwelle_w:897,aktuell_w:-6397,mittel_w:-6100,mittel_bereit:false,phasen:1,min_w:1380,pv_anteil:65}};
  const root=rowCard({ev:[['sensor.ev','status','waiting',gateAttrs],['select.ev_goal','goal','pv_only',{options:['pv_only','km_until','days','now']}]]});
  const icons=[...root.querySelectorAll('.sep-gates .sep-gate')].map(i=>i.getAttribute('icon'));
  assert.deepEqual(icons,['mdi:history','mdi:scale-balance'],'H and B, no trend');
  root.querySelector('[data-log]').click();
  const log=root.querySelector('.sep-log').textContent;
  assert.match(log,/Soll ≥ 897 W/);
  assert.match(log,/2-min-Ø Ist -6100 W|2-min-Ø Ist −6100 W|2-min-Ø Ist -6.100 W|2-min-Ø Ist/);
  assert.match(log,/1380 W|1.380 W/);
  // charging: no start check
  const charging=rowCard({ev:[['sensor.ev','status','charging_pv',{geraetetyp:'ev',modus:'auto',pv_startpruefung:null}]]});
  assert.equal(charging.querySelector('.sep-gates'),null);
});

test('PV forecast tile identifies its active source without losing remaining kWh',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:false});
  dom.window.document.body.appendChild(card);
  const hub='hub';
  const entities={
    plan:{platform:'smartify_energy',translation_key:'plan',device_id:hub,entity_id:'sensor.plan'},
    forecast:{platform:'smartify_energy',translation_key:'forecast_today',device_id:hub,entity_id:'sensor.fc'},
  };
  const states={
    'sensor.plan':{state:'-',attributes:{stunden:[]}},
    'sensor.fc':{state:'12.5',last_updated:'2026-11-08T14:00:00Z',attributes:{rest_heute_kwh:7.2,prognose_quelle:'Solcast',prognose_modus:'external'}},
  };
  card.hass={entities,states,devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  let tile=card.shadowRoot.querySelector('.forecast-source');
  assert.ok(tile,'source should be visible in the tile');
  assert.match(tile.textContent,/Quelle: Solcast/);
  assert.match(card.shadowRoot.textContent,/Rest 7.2 kWh/);
  card.setConfig({show_timeline:true});
  let planTitle=[...card.shadowRoot.querySelectorAll(".section")].find(x=>x.textContent.includes("PV-Plan"));
  assert.match(planTitle.textContent,/Solcast/);
  states['sensor.fc']={state:'8.1',last_updated:'2026-11-08T14:15:00Z',attributes:{rest_heute_kwh:4.3,prognose_quelle:'Eigene Berechnung',prognose_modus:'calculated'}};
  card.hass={entities,states,devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  tile=card.shadowRoot.querySelector('.forecast-source');
  assert.match(tile.textContent,/Eigene Berechnung/);
  assert.doesNotMatch(tile.textContent,/Solcast/);
  planTitle=[...card.shadowRoot.querySelectorAll(".section")].find(x=>x.textContent.includes("PV-Plan"));
  assert.match(planTitle.textContent,/Eigene Berechnung/);
});


test('PV plan has an initially collapsed, clickable actual-vs-forecast chart',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_priorities:false,show_header:false,show_timeline:true});
  dom.window.document.body.append(card);
  const hub='hub';
  const entities={plan:{platform:'smartify_energy',translation_key:'plan',device_id:hub,entity_id:'sensor.plan'}};
  const first=new Date().toISOString();
  const states={'sensor.plan':{state:'–',last_updated:first,attributes:{
    stunden:[],pv_vergleich:{konfiguriert:true,verglichene_stunden:1,
      prognose_kwh:1,ist_kwh:0.8,abweichung_pct:-20,
      stunden:[{zeit:'2026-11-08T08:00:00+00:00',prognose_wh:1000,ist_wh:800},
               {zeit:'2026-11-08T09:00:00+00:00',prognose_wh:1100,ist_wh:null}]}
  }}};
  const hass={entities,states,devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  card.hass=hass;
  const toggle=card.shadowRoot.querySelector('[data-pvcompare]');
  assert.ok(toggle,'expand control must exist below PV plan even if plan timeline is empty');
  assert.equal(toggle.getAttribute('aria-expanded'),'false');
  assert.equal(card.shadowRoot.querySelector('.pv-compare-body'),null);
  toggle.click();
  assert.equal(card.shadowRoot.querySelector('[data-pvcompare]').getAttribute('aria-expanded'),'true');
  assert.match(card.shadowRoot.querySelector('.pv-compare-body').textContent,/0,80 kWh/);
  assert.match(card.shadowRoot.querySelector('.pv-compare-body').textContent,/-20.0 %/);
  assert.equal(card.shadowRoot.querySelectorAll('.pv-compare-forecast').length,2);
  assert.equal(card.shadowRoot.querySelectorAll('.pv-compare-actual').length,1);
  const existing=card.shadowRoot.querySelector('.pv-compare-body');
  states['sensor.plan']={...states['sensor.plan'],last_updated:new Date(Date.now()+1000).toISOString()};
  card.hass=hass;
  assert.ok(card.shadowRoot.querySelector('.pv-compare-body'),'expanded state survives HA refresh');
  card.shadowRoot.querySelector('[data-pvcompare]').click();
  assert.equal(card.shadowRoot.querySelector('.pv-compare-body'),null);
});

test('PV comparison reports missing PV generation meter rather than inventing actuals',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false});
  dom.window.document.body.append(card);
  card.hass={entities:{plan:{platform:'smartify_energy',translation_key:'plan',device_id:'hub',entity_id:'sensor.plan'}},
    states:{'sensor.plan':{state:'–',attributes:{stunden:[],pv_vergleich:{konfiguriert:false,stunden:[]}}}},
    devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  card.shadowRoot.querySelector('[data-pvcompare]').click();
  assert.match(card.shadowRoot.querySelector('.pv-compare-body').textContent,/PV-Erzeugungsleistung/);
  assert.equal(card.shadowRoot.querySelectorAll('.pv-compare-actual').length,0);
});


test('PV comparison supports a 48h scrollback including missing hours',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false});
  dom.window.document.body.append(card);
  const base=Date.parse('2026-11-08T00:00:00Z');
  const slots=Array.from({length:48},(_,i)=>({
    zeit:new Date(base+i*3600000).toISOString(),
    prognose_wh:i===5 ? null : 400+i,
    ist_wh:i<=35 ? 300+i : null
  }));
  card.hass={
    entities:{plan:{platform:'smartify_energy',translation_key:'plan',device_id:'hub',entity_id:'sensor.plan'}},
    states:{'sensor.plan':{state:'–',attributes:{stunden:[],pv_vergleich:{konfiguriert:true,
      stunden:slots,prognose_kwh:10,ist_kwh:9,abweichung_pct:-10,verglichene_stunden:35}}}},
    devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}
  };
  card.shadowRoot.querySelector('[data-pvcompare]').click();
  const root=card.shadowRoot;
  assert.match(root.querySelector('[data-pvcompare]').textContent,/48 h/);
  assert.equal(root.querySelectorAll('.pv-compare-col').length,48);
  assert.equal(root.querySelectorAll('.pv-compare-forecast').length,47);
  assert.equal(root.querySelectorAll('.pv-compare-actual').length,36);
  assert.match(root.querySelector('.pv-compare-plot').getAttribute('style'),/2160px/);
  assert.match(root.querySelectorAll('.pv-compare-col')[5].getAttribute('title'),/kein Wert/);
  assert.ok(root.querySelector('.pv-compare-scroll'));
});


test('PV plan shows readable kW axis with 4 aligned horizontal guide lines',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  const now=Date.now();
  const soon=new Date(now-now%3600000+3600000).toISOString();
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false});
  dom.window.document.body.append(card);
  card.hass={entities:{plan:{platform:'smartify_energy',translation_key:'plan',device_id:'hub',entity_id:'sensor.plan'}},
    states:{'sensor.plan':{state:'–',last_updated:new Date().toISOString(),attributes:{
      stunden:[{zeit:soon,pv_w:4300,frei_w:2000,geraete:{Waschmaschine:1800}}]}}},
    devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  const plot=card.shadowRoot.querySelector('.timeline .bars');
  const axis=card.shadowRoot.querySelector('.timeline .sep-y-axis');
  assert.ok(plot,'PV plan chart exists');
  assert.equal(plot.querySelectorAll('.sep-chart-grid i').length,4);
  assert.equal(axis.querySelectorAll('span').length,5);
  assert.match(axis.textContent,/kW/);
  assert.equal(axis.querySelector('span').textContent,'5 kW','max 4.3 kW uses rounded 5 kW axis');
  assert.equal(axis.querySelector('span:last-child').textContent,'0 kW');
  assert.match(plot.querySelector('.col .pv').getAttribute('style'),/86%/);
});

test('PV actual-forecast comparison uses fixed left kWh axis while scrolling 48h',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false});
  dom.window.document.body.append(card);
  const start=Date.parse('2026-11-07T00:00:00Z');
  const slots=Array.from({length:48},(_,i)=>({zeit:new Date(start+i*3600000).toISOString(),
    prognose_wh:2500,ist_wh:i<40?2000:null}));
  card.hass={entities:{plan:{platform:'smartify_energy',translation_key:'plan',device_id:'hub',entity_id:'sensor.plan'}},
    states:{'sensor.plan':{state:'–',attributes:{stunden:[],pv_vergleich:{konfiguriert:true,
      stunden:slots,prognose_kwh:90,ist_kwh:72,abweichung_pct:-20,verglichene_stunden:40}}}},
    devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  card.shadowRoot.querySelector('[data-pvcompare]').click();
  const root=card.shadowRoot;
  const axis=root.querySelector('.pv-compare-body .sep-y-axis');
  const scroll=root.querySelector('.pv-compare-scroll');
  assert.ok(axis && scroll);
  assert.ok(!scroll.contains(axis),'labels stay visible while chart scrolls');
  assert.equal(root.querySelectorAll('.pv-compare-plot .sep-chart-grid i').length,4);
  assert.equal(axis.querySelectorAll('span').length,5);
  assert.equal(axis.querySelector('span').textContent,'2,5 kWh');
  assert.equal(axis.querySelector('span:last-child').textContent,'0 kWh');
  assert.match(root.querySelector('.pv-compare-forecast').getAttribute('style'),/100%/);
});
