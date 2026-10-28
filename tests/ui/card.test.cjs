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

test('trend arrow display is limited to load and heat pump with coverage indicator',()=>{
  assert.match(source,/\["load", "heatpump"\]\.includes\(a\.geraetetyp\)/);
  assert.match(source,/mdi:arrow-top-right/);
  assert.match(source,/mdi:arrow-bottom-right/);
  assert.match(source,/trend_history_min/);
  assert.match(source,/trend_ready/);
});

test('short-window arrow follows the three-gate threshold and neutral rule',()=>{
  const dom=new JSDOM('<div></div>',{runScripts:'outside-only'});
  dom.window.eval(source+'\nwindow.deviceTrendTest=deviceTrend;');
  const trend=dom.window.deviceTrendTest;
  assert.equal(trend(2200,2000,-500,100,true).direction,'down',
    'falling below threshold blocks despite enough current short average');
  assert.equal(trend(2400,2000,-300,100,true).allowed,true,
    'falling but projected above requirement remains allowed');
  assert.equal(trend(1900,2000,0,100,true).direction,'neutral');
  assert.equal(trend(1900,2000,-50,100,true).allowed,true);
  assert.equal(trend(1900,2000,-250,100,true).direction,'down');
  assert.equal(trend(1900,2000,-250,100,true).allowed,false);
  assert.equal(trend(1900,2000,250,100,false).direction,'pending');
  assert.equal(trend(null,2000,300,100,true).direction,'pending');
});

test('trend row labels average, trend window and stored data age separately',()=>{
  assert.match(source,/const avgWindow = num\(this\._st\(d\.ents\["number:avg_window"\]\)\?\.state\)/);
  assert.match(source,/\$\{avgWindow \?\? "–"\} min History/);
  assert.match(source,/\$\{trendWindow \?\? "–"\} min Trend/);
  assert.match(source,/trendAge/);
});

test('compact priority rows expose history readiness and trend instead of redundant average',()=>{
  assert.match(source,/history_avg_ready/);
  assert.match(source,/min History/);
  assert.match(source,/min Trend/);
  assert.match(source,/Sollwert/);
  assert.match(source,/Neues Programm wird autom\. erkannt/);
  assert.doesNotMatch(source,/<div class="pb-extra">/);
});
