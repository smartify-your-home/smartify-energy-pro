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
