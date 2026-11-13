const {test} = require("node:test");
const assert = require("node:assert/strict");
const {pathToFileURL} = require("node:url");
const fs = require("node:fs");
const source = fs.readFileSync("custom_components/smartify_energy/www/smartify-energy-plan-card.js","utf8");

const chartModule = import(pathToFileURL(
  require("node:path").resolve("custom_components/smartify_energy/www/sep-echarts.mjs")).href);

const theme={text:"#fff",muted:"#aaa",grid:"#333",pv:"#f90",
  compareForecast:"#eea",compareActual:"#2a7",planned:"#28e"};

test("ECharts is bundled locally; a separate Lovelace card is not required",()=>{
  const init=fs.readFileSync("custom_components/smartify_energy/__init__.py","utf8");
  const adapter=fs.readFileSync("custom_components/smartify_energy/www/sep-echarts.mjs","utf8");
  const vendor=fs.readFileSync("custom_components/smartify_energy/www/echarts.simple.min.js","utf8");
  assert.match(init,/StaticPathConfig\(ECHARTS_URL/);
  assert.match(init,/StaticPathConfig\(ECHARTS_ADAPTER_URL/);
  assert.match(adapter,/\/smartify_energy\/echarts\.simple\.min\.js/);
  assert.doesNotMatch(adapter,/https?:\/\/(?!example)/);
  assert.match(vendor,/Apache License/);
  assert.match(source,/use_echarts: true/);
  assert.match(source,/id="use_echarts"/);
  assert.match(source,/if \(!old\.hasAttribute\("data-sep-echarts"\)\) patchChildren/);
  assert.doesNotMatch(init,/add_extra_js_url/);
});

test("PV plan preserves forecast gaps and current+future hour order",async()=>{
  const {sepPlanChart}=await chartModule;
  const stamp="2026-11-14T10:00:00+00:00";
  const now=Date.parse("2026-11-14T08:00:00Z");
  const rows=[
    {zeit:"2026-11-14T12:00:00+00:00",pv_w:null,prognose_verfuegbar:false,geraete:{}},
    {zeit:stamp,pv_w:2840,prognose_verfuegbar:true,geraete:{"Waschmaschine":1100}},
    {zeit:"2026-11-14T11:00:00+00:00",pv_w:0,prognose_verfuegbar:true,geraete:{}},
  ];
  const c=sepPlanChart(rows,theme,now);
  assert.deepEqual(c.options.series[0].data,[2.84,0,null]);
  assert.deepEqual(c.options.series[1].data,[1.1,null,null]);
  assert.match(c.options.tooltip.formatter([{dataIndex:2,seriesName:"PV-Prognose",value:null}]),/Keine Prognose/);
  assert.ok(c.width>=640);
  assert.equal(sepPlanChart([],theme,now),null);
});

test("14-day comparison has exact STC peak scale and missing values stay missing",async()=>{
  const {sepComparisonChart}=await chartModule;
  const data={gesamt_peak_kwp:10,zeitzone:"Europe/Vienna",
    tageslicht:[{datum:"2026-11-14",sonnenaufgang:"2026-11-14T06:15:00Z",sonnenuntergang:"2026-11-14T15:20:00Z"}],
    stunden:[
    {zeit:"2026-11-14T10:00:00Z",prognose_wh:9200,ist_wh:10800},
    {zeit:"2026-11-14T11:00:00Z",prognose_wh:6500,ist_wh:null},
    {zeit:"2026-11-14T12:00:00Z",prognose_wh:null,ist_wh:0},
  ]};
  const c=sepComparisonChart(data,theme);
  assert.equal(c.options.yAxis.max,10);
  assert.deepEqual(c.options.series[0].data,[9.2,6.5,null]);
  assert.deepEqual(c.options.series[1].data,[10.8,null,0]);
  assert.match(c.options.tooltip.formatter([{dataIndex:1,seriesName:"Ist-Erzeugung"}]),/Ist: –/);
  assert.equal(sepComparisonChart({...data,gesamt_peak_kwp:0},theme),null);
});

test("Apex-free ECharts controller disposes on unload and does not repeat setOption",async()=>{
  const {SEPChartController,sepPlanChart}=await chartModule;
  const prior=global.window;
  let updates=0,disposals=0,resize=0,clicked=null;
  const chart={
    setOption(){updates++;},dispose(){disposals++;},
    resize(){resize++;},off(){},on(name,cb){if(name==="click")clicked=cb;}
  };
  global.window={echarts:{init:()=>chart}};
  try{
    const wrapper={classList:{add(){} }};
    const host={isConnected:true,style:{},classList:{add(){}},closest:()=>wrapper};
    const ctrl=new SEPChartController();
    const c=sepPlanChart([
      {zeit:"2026-11-14T10:00:00Z",pv_w:3000,prognose_verfuegbar:true,geraete:{}}
    ],theme,Date.parse("2026-11-14T08:00:00Z"));
    assert.equal(await ctrl.paint(host,"plan",c,row=>{clicked=row;}),true);
    assert.equal(updates,1);
    assert.equal(await ctrl.paint(host,"plan",c),true);
    assert.equal(updates,1);
    ctrl.cleanup(new Set());
    assert.equal(disposals,1);
  }finally{global.window=prior;}
});

test("Card retains native graphical fallback, device schedule, day summary and theme",()=>{
  assert.match(source,/this\._echartsFailed = true/);
  assert.match(source,/\.sep-echarts-active>\.sep-axis-layout\{display:none\}/);
  assert.match(source,/this\._echartsController\?\.destroy\(\)/);
  assert.match(source,/pv-compare-days/);
  assert.match(source,/pv-plan-days/);
  assert.match(source,/this\._updatePVSelectedDay\(scroll\)/);
  assert.match(source,/sepEChartsTheme/);
});
