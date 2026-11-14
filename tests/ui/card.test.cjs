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
    stunden:[],pv_vergleich:{konfiguriert:true,gesamt_peak_kwp:2.5,verglichene_stunden:1,
      prognose_kwh:1,ist_kwh:0.8,abweichung_pct:-20,
      stunden:[{zeit:'2026-11-08T08:00:00+00:00',prognose_wh:1000,ist_wh:800},
               {zeit:'2026-11-08T09:00:00+00:00',prognose_wh:1100,ist_wh:null}]}
  }}};
  const hass={entities,states,devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  card.hass=hass;
  assert.ok(card.shadowRoot.querySelector('.pv-compare-body'),
    'comparison chart must always be visible even with an empty PV plan');
  assert.equal(card.shadowRoot.querySelector('[data-pvcompare]'),null);
  assert.match(card.shadowRoot.querySelector('.pv-compare-body').textContent,/0,80 kWh/);
  assert.match(card.shadowRoot.querySelector('.pv-compare-body').textContent,/-20.0 %/);
  assert.equal(card.shadowRoot.querySelectorAll('.pv-compare-forecast').length,2);
  assert.equal(card.shadowRoot.querySelectorAll('.pv-compare-actual').length,1);
  states['sensor.plan']={...states['sensor.plan'],last_updated:new Date(Date.now()+1000).toISOString()};
  card.hass=hass;
  assert.ok(card.shadowRoot.querySelector('.pv-compare-body'),'visible state survives HA refresh');
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
    states:{'sensor.plan':{state:'–',attributes:{stunden:[],pv_vergleich:{konfiguriert:true,gesamt_peak_kwp:2.5,
      stunden:slots,prognose_kwh:10,ist_kwh:9,abweichung_pct:-10,verglichene_stunden:35}}}},
    devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}
  };
  const root=card.shadowRoot;
  assert.equal(root.querySelectorAll('.pv-compare-col').length,48);
  assert.equal(root.querySelectorAll('.pv-compare-forecast').length,47);
  assert.equal(root.querySelectorAll('.pv-compare-actual').length,36);
  assert.match(root.querySelector('.pv-compare-scroll > div').getAttribute('style'),/2160px/);
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
    states:{'sensor.plan':{state:'–',attributes:{stunden:[],pv_vergleich:{konfiguriert:true,gesamt_peak_kwp:2.5,
      stunden:slots,prognose_kwh:90,ist_kwh:72,abweichung_pct:-20,verglichene_stunden:40}}}},
    devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  const root=card.shadowRoot;
  const axis=root.querySelector('.pv-compare-body .sep-y-axis');
  const scroll=root.querySelector('.pv-compare-scroll');
  assert.ok(axis && scroll);
  assert.ok(!scroll.contains(axis),'labels stay visible while chart scrolls');
  assert.equal(root.querySelectorAll('.pv-compare-plot .sep-chart-grid i').length,4);
  assert.equal(axis.querySelectorAll('span').length,5);
  assert.equal(axis.querySelector('span').textContent,'2,5 kWh');
  assert.equal(axis.querySelector('span:last-child').textContent,'0 kWh');
  assert.equal(root.querySelector('.pv-compare-forecast').getAttribute('style'),'height:100%');
  assert.equal(root.querySelectorAll('.pv-compare-day-divider').length,1);
  assert.equal(root.querySelector('.sep-y-axis.compare').getAttribute('class'),'sep-y-axis compare');
});

test('PV comparison hides night hours using HA sunrise/sunset, keeps edge hours and day headings',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false});
  dom.window.document.body.append(card);
  const base=Date.parse('2026-11-08T00:00:00+01:00');
  const slots=Array.from({length:48},(_,i)=>({zeit:new Date(base+i*3600000).toISOString(),
    prognose_wh:1000,ist_wh:800}));
  const sunlight=[8,9].map(day=>({datum:`2026-11-${String(day).padStart(2,'0')}`,
    sonnenaufgang:`2026-11-${String(day).padStart(2,'0')}T07:00:00+01:00`,
    sonnenuntergang:`2026-11-${String(day).padStart(2,'0')}T16:00:00+01:00`}));
  card.hass={entities:{plan:{platform:'smartify_energy',translation_key:'plan',device_id:'hub',entity_id:'sensor.plan'}},
    states:{'sensor.plan':{state:'–',attributes:{stunden:[],pv_vergleich:{konfiguriert:true,gesamt_peak_kwp:2.5,
      stunden:slots,tageslicht:sunlight,zeitzone:"Europe/Vienna",prognose_kwh:20,ist_kwh:16,abweichung_pct:-20,verglichene_stunden:20}}}},
    devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  const root=card.shadowRoot;
  assert.equal(root.querySelectorAll('.pv-compare-col').length,22);
  assert.equal(root.querySelectorAll('.pv-compare-day').length,2);
  assert.equal(root.querySelectorAll('.pv-compare-hour-pct').length,22);
  assert.equal(root.querySelectorAll('.pv-compare-day-divider').length,1,'each local day switch has a full-height divider');
  assert.ok(root.querySelector('.pv-compare-col .pv-compare-hour-pct').getAttribute('style').includes('bottom:calc('));
  assert.match(root.querySelector('.pv-compare-hour-pct').textContent,/-20.0 %/);
  assert.match(root.querySelector('.pv-compare-day').textContent,/-20.0 %/);
  assert.equal(root.querySelectorAll('.pv-compare-col.day-start').length,2);
});


test('PV chart uses installed total peak rather than a 14-day historical outlier',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false});
  dom.window.document.body.append(card);
  const hours=[0,1,2].map(i=>({zeit:new Date(Date.parse('2026-11-09T09:00:00+01:00')+i*3600000).toISOString(),
    prognose_wh:i===2?8000:2000,ist_wh:1200}));
  card.hass={entities:{plan:{platform:'smartify_energy',translation_key:'plan',device_id:'hub',entity_id:'sensor.plan'}},
    states:{'sensor.plan':{state:'–',attributes:{stunden:[],pv_vergleich:{konfiguriert:true,
      gesamt_peak_kwp:10.6,stunden:hours,prognose_kwh:4,ist_kwh:3,abweichung_pct:-25,verglichene_stunden:3}}}},
    devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  const root=card.shadowRoot;
  assert.equal(root.querySelector('.pv-compare-body .sep-y-axis span').textContent,'10,6 kWh',
    '10.6 kWp is exactly 10.6 kWh on the fixed scale, independent of 8 kWh historical value');
  assert.equal(root.querySelectorAll('.pv-compare-percentages').length,0);
  const deviation=root.querySelector('.pv-compare-col .pv-compare-hour-pct');
  assert.ok(deviation && deviation.getAttribute('style').includes('bottom:calc('));
  assert.equal(root.querySelectorAll('.pv-compare-col').length,3);
});


test('PV summary follows horizontally visible day; no 14-day aggregate displayed',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false});
  dom.window.document.body.append(card);
  const base=Date.parse('2026-11-08T00:00:00+01:00');
  const slots=Array.from({length:48},(_,i)=>{
    const day=i<24?8:9;
    const hour=i%24;
    return {zeit:new Date(base+i*3600000).toISOString(),
      prognose_wh: hour>=7&&hour<=17 ? 1000:null,
      ist_wh: hour>=7&&hour<=17 ? (day===8?800:1200):null};
  });
  const sunlight=[8,9].map(day=>({datum:`2026-11-${String(day).padStart(2,'0')}`,
    sonnenaufgang:`2026-11-${String(day).padStart(2,'0')}T07:00:00+01:00`,
    sonnenuntergang:`2026-11-${String(day).padStart(2,'0')}T18:00:00+01:00`}));
  card.hass={entities:{plan:{platform:'smartify_energy',translation_key:'plan',device_id:'hub',entity_id:'sensor.plan'}},
    states:{'sensor.plan':{state:'–',attributes:{stunden:[],pv_vergleich:{
      konfiguriert:true,gesamt_peak_kwp:10,zeitzone:'Europe/Vienna',tageslicht:sunlight,
      stunden:slots,prognose_kwh:22,ist_kwh:22,abweichung_pct:0,verglichene_stunden:22}}}},
    devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  const root=card.shadowRoot, scroll=root.querySelector('.pv-compare-scroll');
  assert.equal(root.querySelectorAll('.pv-compare-day').length,2);
  // jsdom has no layout engine; simulate the measured horizontal viewport.
  Object.defineProperty(scroll,'scrollWidth',{configurable:true,value:1170});
  Object.defineProperty(scroll,'clientWidth',{configurable:true,value:180});
  scroll.scrollLeft=990;
  scroll.dispatchEvent(new dom.window.Event('scroll',{bubbles:false}));
  assert.match(root.querySelector('[data-pv-selected-date]').textContent,/09.11.2026/);
  assert.equal(root.querySelector('[data-pv-day-forecast]').textContent,'11,00 kWh');
  assert.equal(root.querySelector('[data-pv-day-actual]').textContent,'13,20 kWh');
  assert.equal(root.querySelector('[data-pv-day-deviation]').textContent,'+20.0 %');
  assert.doesNotMatch(root.querySelector('.pv-compare-totals').textContent,/22,00 kWh/);
  scroll.scrollLeft=0;
  scroll.dispatchEvent(new dom.window.Event('scroll',{bubbles:false}));
  assert.match(root.querySelector('[data-pv-selected-date]').textContent,/08.11.2026/);
  assert.equal(root.querySelector('[data-pv-day-forecast]').textContent,'11,00 kWh');
  assert.equal(root.querySelector('[data-pv-day-actual]').textContent,'8,80 kWh');
  assert.equal(root.querySelector('[data-pv-day-deviation]').textContent,'-20.0 %');
  scroll.scrollLeft=1000;
  scroll.dispatchEvent(new dom.window.Event('scroll',{bubbles:false}));
  assert.equal(root.querySelector('[data-pv-day-deviation]').textContent,'+20.0 %');
  // New sensor events must keep the selected calendar day, not reset to 14-day totals.
  card.hass={...card._hass,states:{...card._hass.states,
    'sensor.plan':{...card._hass.states['sensor.plan'],last_updated:new Date().toISOString()}}};
  assert.equal(root.querySelector('[data-pv-day-deviation]').textContent,'+20.0 %');
});

test('PV selected-day summary shows incomplete hours as missing rather than zero',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false});
  dom.window.document.body.append(card);
  card.hass={entities:{plan:{platform:'smartify_energy',translation_key:'plan',device_id:'hub',entity_id:'sensor.plan'}},
    states:{'sensor.plan':{state:'–',attributes:{stunden:[],pv_vergleich:{konfiguriert:true,
      gesamt_peak_kwp:5,stunden:[{zeit:'2026-11-09T09:00:00+01:00',prognose_wh:1200,ist_wh:null}],
      prognose_kwh:null,ist_kwh:null,abweichung_pct:null,verglichene_stunden:0}}}},
    devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  const root=card.shadowRoot;
  assert.equal(root.querySelector('[data-pv-day-actual]').textContent,'–');
  assert.equal(root.querySelector('[data-pv-day-forecast]').textContent,'–');
  assert.equal(root.querySelector('[data-pv-day-deviation]').textContent,'–');
  assert.match(root.querySelector('[data-pv-selected-date]').textContent,/bisher/);
});


test('PV plan scrolls into tomorrow and day after with pinned kW scale and tip carousel',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false,show_pv_tips:true});
  dom.window.document.body.append(card);
  const now=new Date(),hour=new Date(now);hour.setMinutes(0,0,0);hour.setHours(hour.getHours()+1);
  const entries=[];
  for(let i=0;i<3;i++){
    const d=new Date(hour);d.setDate(d.getDate()+i);
    for(let h=0;h<3;h++){
      const ts=new Date(d);ts.setHours(d.getHours()+h);
      entries.push({zeit:ts.toISOString(),pv_w:1600+i*1000,frei_w:700+i*1000,geraete:{Waschmaschine:500}});
    }
  }
  const entities={
    plan:{platform:'smartify_energy',translation_key:'plan',device_id:'hub',entity_id:'sensor.plan'},
    tip:{platform:'smartify_energy',translation_key:'pv_tipp',device_id:'hub',entity_id:'sensor.tip'},
  };
  const stamp=now.toISOString();
  const states={
    'sensor.plan':{state:'–',last_updated:stamp,attributes:{stunden:entries}},
    'sensor.tip':{state:'Wäsche besser morgen',last_updated:stamp,attributes:{tipps:[
      {text:'Wäsche besser morgen',detail:'08–16 Uhr · +4,8 kWh (+38 %)',icon:'mdi:washing-machine'},
      {text:'E-Auto morgen laden',detail:'PV-Fenster',icon:'mdi:ev-station'},
    ]}},
  };
  card.hass={entities,states,devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}};
  const root=card.shadowRoot;
  const scroll=root.querySelector('.pv-plan-scroll');
  assert.ok(scroll,'timeline has horizontal scroll container');
  assert.ok(root.querySelectorAll('.pv-plan-day').length>=2,'day headings across forecast');
  assert.ok(!scroll.contains(root.querySelector('.sep-y-axis')),'kW scale fixed outside scroller');
  assert.match(root.querySelector('.pv-tip').textContent,/Wäsche besser morgen/);
  root.querySelector('[data-pvtip="1"]').click();
  assert.match(root.querySelector('.pv-tip').textContent,/E-Auto morgen laden/);
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false,show_pv_tips:false});
  assert.equal(root.querySelector('.pv-tip'),null,'per-card toggle hides overlay entirely');
  assert.equal(states['sensor.tip'].state,'Wäsche besser morgen','tip sensor is independent');
});

test('PV advice visibility lives only in the Lovelace card editor',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const editor=dom.window.document.createElement('smartify-energy-plan-card-editor');
  editor.setConfig({show_timeline:true});
  dom.window.document.body.append(editor);
  const check=editor.shadowRoot.getElementById('show_pv_tips');
  assert.ok(check && check.checked,'visible by default');
  let conf;
  editor.addEventListener('config-changed',e=>{conf=e.detail.config;});
  check.checked=false;
  check.dispatchEvent(new dom.window.Event('change'));
  assert.equal(conf.show_pv_tips,false);
});


test('PV plan can navigate to overmorgen when weather hours are missing, without fake bars',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false});
  dom.window.document.body.append(card);
  const tomorrow=new Date();
  tomorrow.setHours(10,0,0,0);
  tomorrow.setDate(tomorrow.getDate()+1);
  const entries=[0,1,2].map(i=>{
    const hour=new Date(tomorrow);hour.setHours(10+i);
    return {zeit:hour.toISOString(),pv_w:2400,frei_w:1600,geraete:{},
      prognose_verfuegbar:true};
  });
  const e={plan:{platform:'smartify_energy',translation_key:'plan',
    device_id:'hub',entity_id:'sensor.sep_plan'}};
  card.hass={entities:e,devices:{hub:{name:'SEP'}},
    states:{'sensor.sep_plan':{state:'–',last_updated:new Date().toISOString(),
      attributes:{stunden:entries,prognose_bis:entries.at(-1).zeit,
        wetter_sensor:'sensor.meteonomiqs_cloud_forecast_8h'}}},
    callService(){return Promise.resolve()}};
  const root=card.shadowRoot;
  const days=[...root.querySelectorAll('.pv-plan-day')];
  assert.equal(days.length,2,'morgen plus missing übermorgen are both displayed');
  assert.match(root.querySelector('.pv-plan-missing').textContent,/keine vollständige Stundenprognose/);
  assert.match(root.querySelector('.pv-plan-coverage').textContent,/48h/);
  assert.equal(root.querySelectorAll('.bars > .col').length,3,'no invented overmorgen PV columns');
  assert.equal(root.querySelector('.pv-plan-day-nav'),null,'day navigation buttons are hidden');
  assert.equal(root.querySelector('.pv-plan-controls'),null,'no redundant scroll instruction');
  assert.ok(root.querySelector('.pv-plan-scroll'),'horizontal scroll remains available');
});

test('PV plan shows real übermorgen bars without missing marker when full forecast exists',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false,show_pv_tips:false});
  dom.window.document.body.append(card);
  const entries=[];
  for(let offset=1;offset<=2;offset++){
    const day=new Date();day.setDate(day.getDate()+offset);
    for(let hour=8;hour<16;hour++){
      const stamp=new Date(day);stamp.setHours(hour,0,0,0);
      entries.push({zeit:stamp.toISOString(),pv_w:offset*1100,frei_w:offset*800,geraete:{},
        prognose_verfuegbar:true});
    }
  }
  card.hass={entities:{plan:{platform:'smartify_energy',translation_key:'plan',
    device_id:'hub',entity_id:'sensor.sep_plan'}},devices:{hub:{name:'SEP'}},
    states:{'sensor.sep_plan':{state:'–',last_updated:new Date().toISOString(),
      attributes:{stunden:entries,prognose_bis:entries.at(-1).zeit}}},
    callService(){return Promise.resolve()}};
  const root=card.shadowRoot;
  assert.equal(root.querySelectorAll('.pv-plan-day').length,2);
  assert.equal(root.querySelectorAll('.bars > .col').length,16);
  assert.equal(root.querySelector('.pv-plan-missing'),null);
  assert.equal(root.querySelector('.pv-plan-coverage'),null);
});

test('PV tip stays above bars with 16px headline and 14px detail, without scroll toolbar',()=>{
  assert.match(source,/\.pv-tip-title\{font-size:16px;/);
  assert.match(source,/\.pv-tip-detail\{font-size:14px;/);
  assert.doesNotMatch(source,/data-pvplan/);
  assert.doesNotMatch(source,/pv-plan-controls/);
  assert.match(source,/\.pv-plan-scroll\{overflow-x:auto/);
  assert.match(source,/data-pvtip/,'tip carousel arrows remain usable');
});


test('PV comparison exact peak scale stays at 10 kWh even with larger historic values',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_timeline:true,show_priorities:false,show_header:false});
  dom.window.document.body.append(card);
  const slots=[{zeit:'2026-11-11T12:00:00+01:00',prognose_wh:8400,ist_wh:11000}];
  card.hass={
    entities:{plan:{platform:'smartify_energy',translation_key:'plan',
      device_id:'hub',entity_id:'sensor.plan'}},
    states:{'sensor.plan':{state:'–',attributes:{stunden:[],
      pv_vergleich:{konfiguriert:true,gesamt_peak_kwp:10,stunden:slots}}}},
    devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}
  };
  const root=card.shadowRoot;
  const axis=root.querySelector('.pv-compare-body .sep-y-axis');
  assert.equal(axis.querySelector('span').textContent,'10 kWh');
  assert.equal(axis.querySelector('span:last-child').textContent,'0 kWh');
  assert.equal(root.querySelector('.pv-compare-forecast').getAttribute('style'),'height:84%');
  assert.equal(root.querySelector('.pv-compare-actual').getAttribute('style'),'height:100%',
    'above peak measurement is visually capped, not rescaled');
  assert.match(root.querySelector('.pv-compare-col').getAttribute('title'),/11.00 kWh/,
    'the real above-peak value remains accessible in the tooltip');
});


test('priority lock sits top-left above first row and blocks mobile drag until unlocked',async()=>{
  const root=settingsCard();
  const card=root.host;
  const lock=root.querySelector('.priority-section .priority-lock');
  const row=root.querySelector('.list > .dev-wrap');
  const handle=row.querySelector('.handle');
  assert.ok(lock && row,'lock is placed in priority header above the first device row');
  assert.equal(lock.getAttribute('aria-label'),'Prioritäten entsperren');
  assert.equal(lock.getAttribute('aria-pressed'),'false');
  assert.equal(lock.querySelector('ha-icon').getAttribute('icon'),'mdi:lock');
  assert.ok(handle.classList.contains('locked'),'drag handles muted and touch scroll allowed while locked');
  const services=[];
  card._hass.callService=async (...args)=>{services.push(args);};
  const down=()=>root.querySelector('.list .handle').dispatchEvent(new root.host.ownerDocument.defaultView.MouseEvent('pointerdown',{
    bubbles:true,clientY:20}));
  down();
  assert.equal(card._drag,null,'pointerdown cannot start a drag while locked');
  assert.equal(services.length,0,'no priority writes while locked');

  lock.click();
  assert.equal(card._priorityLocked,false);
  assert.equal(root.querySelector('.priority-lock').getAttribute('aria-pressed'),'true');
  assert.equal(root.querySelector('.priority-lock ha-icon').getAttribute('icon'),'mdi:lock-open-variant');
  assert.ok(!root.querySelector('.list .handle').classList.contains('locked'));
  down();
  assert.ok(card._drag,'unlocked handle starts pointer drag');
  root.querySelector('.list .dev-wrap').dispatchEvent(new root.host.ownerDocument.defaultView.Event('pointercancel',{bubbles:true}));
  await Promise.resolve();
  assert.equal(card._drag,null,'cancel clears the gesture');
  assert.equal(services.length,0,'cancel never submits a priority order');

  root.querySelector('.priority-lock').click();
  assert.equal(card._priorityLocked,true,'can relock without saving another configuration');
  assert.ok(root.querySelector('.list .handle').classList.contains('locked'));
  down();
  assert.equal(card._drag,null,'priority lock still blocks dragging after re-render');
  assert.equal(services.length,0);
});

test('PV plan shows a narrow unlabelled day gap instead of grey Nacht block',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const card=dom.window.document.createElement('smartify-energy-plan-card');
  card.setConfig({show_priorities:false,show_header:false,show_timeline:true,show_pv_tips:false});
  dom.window.document.body.append(card);
  const h1=new Date();h1.setDate(h1.getDate()+1);h1.setHours(14,0,0,0);
  const h2=new Date(h1);h2.setDate(h2.getDate()+1);h2.setHours(9,0,0,0);
  const hours=[h1,h2].map(time=>({zeit:time.toISOString(),pv_w:1200,frei_w:900,
    geraete:{},prognose_verfuegbar:true}));
  card.hass={
    entities:{plan:{platform:'smartify_energy',translation_key:'plan',device_id:'hub',entity_id:'sensor.plan'}},
    states:{'sensor.plan':{state:'–',last_updated:new Date().toISOString(),attributes:{stunden:hours}}},
    devices:{hub:{name:'SEP'}},callService(){return Promise.resolve()}
  };
  const root=card.shadowRoot;
  const gap=root.querySelector('.timeline .pv-break');
  assert.ok(gap,'the gap still separates disjoint forecast hours');
  assert.equal(gap.textContent.trim(),'','neither Nacht nor PV-Pause is displayed');
  assert.match(gap.getAttribute('title'),/ohne PV-Ertrag/,'gap remains explainable by tooltip');
  assert.equal(root.querySelector('.timeline .pv-break-label').textContent.trim(),'');
  assert.match(source,/\.pv-break \{ flex:0 0 12px/,'gap is now a narrow transparent separator');
  assert.match(source,/background:transparent;opacity:\.6/);
  assert.ok(root.querySelectorAll('.pv-plan-day').length>=2,'day headings still mark the new day');
});


test('PV plan and forecast/actual comparison move together above priorities',()=>{
  const root=settingsCard();
  const card=root.host;
  card.setConfig({show_timeline:true,show_priorities:true});
  const order=()=>[...root.querySelectorAll('[data-order-block]')].map(x=>x.dataset.orderBlock);
  assert.deepEqual(order(),['priorities','pv'],'legacy order is the default');
  assert.equal(root.querySelector('[data-order-block="pv"] .pv-compare-body')!=null,true,
    'forecast/actual comparison remains inside the PV block');
  assert.ok(root.querySelector('[data-priority-lock]'),'lock remains in priorities header');
  card._changeSectionOrder(true);
  assert.deepEqual(order(),['pv','priorities'],'drag moves the complete PV block above priorities');
  assert.ok(root.querySelector('[data-order-block="pv"] .pv-compare-body'),
    'comparison remains with PV timeline after reordering');
  assert.equal(card._priorityLocked,true,'section rearrangement does not unlock device priorities');
  card._changeSectionOrder(false);
  assert.deepEqual(order(),['priorities','pv'],'both directions supported');
});

test('live section grip pointer gesture reorders, but short tap or cancellation does not',()=>{
  const root=settingsCard();
  const card=root.host;
  card.setConfig({show_timeline:true,show_priorities:true});
  assert.equal(card._pvPlanFirstOverride,null);
  const grip=root.querySelector('[data-section-grip="pv"]');
  const win=grip.ownerDocument.defaultView;
  const pointer=(name,y)=>new win.MouseEvent(name,{bubbles:true,clientY:y});
  grip.dispatchEvent(pointer('pointerdown',200));
  grip.dispatchEvent(pointer('pointerup',190));
  assert.equal(card._pvPlanFirstOverride,null,'short tap does not modify config');
  grip.dispatchEvent(pointer('pointerdown',200));
  grip.dispatchEvent(pointer('pointercancel',100));
  assert.equal(card._pvPlanFirstOverride,null,'cancelled gesture cannot reorder');
  grip.dispatchEvent(pointer('pointerdown',200));
  grip.dispatchEvent(pointer('pointermove',100));
  grip.dispatchEvent(pointer('pointerup',100));
  assert.equal(card._pvPlanFirstOverride,true,'upward drag brings PV above priorities');
  assert.equal(root.querySelector('[data-order-block]').dataset.orderBlock,'pv');
  const newGrip=root.querySelector('[data-section-grip="pv"]');
  newGrip.dispatchEvent(pointer('pointerdown',100));
  newGrip.dispatchEvent(pointer('pointerup',200));
  assert.equal(card._pvPlanFirstOverride,false,'downward drag reverses order');
});

test('editor saves order in Lovelace card configuration and offers touch-safe fallback',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source);
  const editor=dom.window.document.createElement('smartify-energy-plan-card-editor');
  editor.setConfig({});
  dom.window.document.body.append(editor);
  const names=()=>[...editor.shadowRoot.querySelectorAll('[data-order-item]')].map(x=>x.dataset.orderItem);
  assert.deepEqual(names(),['priorities','pv']);
  let saved;
  editor.addEventListener('config-changed',e=>{saved=e.detail.config;});
  editor.shadowRoot.querySelector('[data-order-item="pv"] [data-order-swap]').click();
  assert.equal(saved.pv_plan_first,true,'editor emitted durable configuration value');
  assert.deepEqual(names(),['pv','priorities']);
  editor.shadowRoot.querySelector('[data-order-item="pv"] [data-order-swap]').click();
  assert.equal(saved.pv_plan_first,false);
  assert.deepEqual(names(),['priorities','pv']);
  editor.setConfig({pv_plan_first:true});
  assert.deepEqual(names(),['pv','priorities'],'saved order restored on editor reload');
});

test('priority heading orders section grip, lock, then label on narrow and wide cards',()=>{
  const root=settingsCard();
  const head=root.querySelector('.priority-section .priority-heading');
  assert.ok(head);
  const buttons=[...head.querySelectorAll(':scope > button')];
  assert.deepEqual(buttons.map(b=>b.hasAttribute('data-section-grip')?'grip':
    b.hasAttribute('data-priority-lock')?'lock':'unknown'),['grip','lock']);
  assert.equal(head.lastChild.textContent.trim(),'Prioritäten');
  assert.equal(buttons[0].getAttribute('data-section-grip'),'priorities');
  assert.equal(buttons[1].getAttribute('aria-label'),'Prioritäten entsperren');
  buttons[1].click();
  const changed=root.querySelector('.priority-section .priority-heading');
  assert.deepEqual([...changed.querySelectorAll(':scope > button')].map(b=>
    b.hasAttribute('data-section-grip')?'grip':'lock'),['grip','lock']);
  assert.equal(changed.querySelector('[data-priority-lock]').getAttribute('aria-label'),'Prioritäten sperren');
});
