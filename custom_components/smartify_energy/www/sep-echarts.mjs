/**
 * Embedded SEP charts with Apache ECharts 6.1.0 (Apache-2.0).
 * Offline, same-origin; no external card, CDN or HA state writes.
 */
const VENDOR_URL = "/smartify_energy/echarts.common.min.js?v=6.1.0";
let vendorPromise = null;

export function loadVendorECharts() {
  if (typeof window !== "undefined" && window.echarts && typeof window.echarts.init === "function")
    return Promise.resolve(window.echarts);
  if (vendorPromise) return vendorPromise;
  vendorPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = VENDOR_URL;
    script.async = true;
    script.onload = () => window.echarts && typeof window.echarts.init === "function"
      ? resolve(window.echarts) : reject(new Error("ECharts is not available after loading"));
    script.onerror = () => reject(new Error("Bundled ECharts script could not load"));
    document.head.appendChild(script);
  }).catch(err => { vendorPromise = null; throw err; });
  return vendorPromise;
}

const color = (value, fallback) => typeof value === "string" && value.trim() ? value.trim() : fallback;
const valueOrNull = v => typeof v === "number" && Number.isFinite(v) && v >= 0 ? v : null;
const dayKey = (value, timeZone) => new Date(value).toLocaleDateString("sv-SE", {timeZone:timeZone || undefined});
const label = (value, timeZone) => new Date(value).toLocaleString("de-AT", {
  timeZone:timeZone || undefined, day:"2-digit", month:"2-digit", hour:"2-digit"
});
const fmt = v => v == null ? "–" : Number(v).toLocaleString("de-AT", {maximumFractionDigits:2});

export function sepEChartsTheme(style) {
  const css = name => style && typeof style.getPropertyValue === "function"
    ? style.getPropertyValue(name).trim() : "";
  return {
    text:color(css("--primary-text-color"), "#dedede"),
    muted:color(css("--secondary-text-color"), "#9e9e9e"),
    grid:color(css("--divider-color"), "#88888844"),
    pv:color(css("--primary-color"), "#e4aa36"),
    compareForecast:color(css("--warning-color"), "#e5a21a"),
    compareActual:color(css("--success-color"), "#22a06b"),
    planned:color(css("--info-color"), "#42a5f5"),
  };
}

function baseOptions(theme, ticks, maxValue=null) {
  return {
    animation:false,
    backgroundColor:"transparent",
    textStyle:{color:theme.text, fontSize:11},
    grid:{left:58,right:15,top:48,bottom:52,containLabel:false},
    legend:{top:0,left:"center",type:"scroll",textStyle:{color:theme.muted,fontSize:11}},
    tooltip:{trigger:"axis",confine:true,renderMode:"richText", textStyle:{fontSize:12}},
    xAxis:{type:"category",boundaryGap:true,data:ticks,
      axisLine:{lineStyle:{color:theme.muted}},
      axisLabel:{color:theme.muted,interval:Math.max(0,Math.ceil(ticks.length/18)-1),
        hideOverlap:true, fontSize:10}},
    yAxis:{type:"value",min:0,...(maxValue!==null?{max:maxValue}:{}),
      name:"kW / kWh",nameTextStyle:{color:theme.muted},
      axisLabel:{color:theme.muted,formatter:value=>Number(value).toLocaleString("de-AT",{maximumFractionDigits:1})},
      splitLine:{lineStyle:{color:theme.grid,type:"dashed"}}},
  };
}

export function sepPlanChart(rows, theme, now=Date.now()) {
  const points = (Array.isArray(rows)?rows:[])
    .filter(row=>row && Number.isFinite(Date.parse(row.zeit)) && Date.parse(row.zeit)+3600000>now)
    .sort((a,b)=>Date.parse(a.zeit)-Date.parse(b.zeit));
  if(!points.length)return null;
  const opt=baseOptions(theme, points.map(row=>label(row.zeit)));
  opt.yAxis.name="kW";
  opt.series=[
    {
      name:"PV-Prognose",type:"line",symbol:"none",smooth:false,connectNulls:false,
      lineStyle:{width:2,color:theme.pv},itemStyle:{color:theme.pv},
      areaStyle:{opacity:0.09,color:theme.pv},
      data:points.map(row=>row.prognose_verfuegbar===false || valueOrNull(row.pv_w)===null
        ? null : Number((row.pv_w/1000).toFixed(3)))
    },
    {
      name:"Geräteplanung",type:"bar",barMaxWidth:14,
      itemStyle:{color:theme.planned,opacity:0.8},
      data:points.map(row=>{
        const values=Object.values(row.geraete||{});
        if(!values.length)return null;
        const sum=values.filter(v=>Number.isFinite(Number(v))&&Number(v)>=0)
          .reduce((acc,v)=>acc+Number(v),0);
        return Number((sum/1000).toFixed(3));
      })
    }
  ];
  opt.tooltip.formatter=params=>{
    if(!params?.length)return "";
    const i=params[0].dataIndex;
    const header=label(points[i].zeit);
    const details=params.map(p=>p.value==null?"":p.seriesName+": "+fmt(p.value)+" kW")
      .filter(Boolean).join("\n");
    return header+(details?"\n"+details:"\nKeine Prognose");
  };
  return {options:opt,rows:points,width:Math.max(640,points.length*51)};
}

export function sepComparisonRows(data) {
  if(!data || !Array.isArray(data.stunden))return [];
  const zone=data.zeitzone||undefined;
  const windows=new Map((data.tageslicht||[]).map(x=>[x.datum,x]));
  return data.stunden.filter(x=>{
    const t=Date.parse(x?.zeit);
    if(!Number.isFinite(t))return false;
    const daylight=windows.get(dayKey(x.zeit,zone));
    if(daylight){
      const sunrise=Date.parse(daylight.sonnenaufgang),sunset=Date.parse(daylight.sonnenuntergang);
      if(Number.isFinite(sunrise)&&Number.isFinite(sunset))
        return t+3600000>sunrise-3600000 && t<sunset+3600000;
    }
    return valueOrNull(x.prognose_wh)>0 || valueOrNull(x.ist_wh)>0;
  });
}

export function sepComparisonChart(data, theme) {
  const rows=sepComparisonRows(data);
  const peak=Number(data?.gesamt_peak_kwp);
  if(!rows.length || !Number.isFinite(peak) || peak<=0)return null;
  const opt=baseOptions(theme,rows.map(x=>label(x.zeit,data.zeitzone)),peak);
  opt.yAxis.name="kWh";
  opt.series=[
    {name:"Ursprüngliche Prognose",type:"bar",barMaxWidth:15,barGap:"10%",
      itemStyle:{color:theme.compareForecast},
      data:rows.map(x=>valueOrNull(x.prognose_wh)===null?null:Number((x.prognose_wh/1000).toFixed(3)))},
    {name:"Ist-Erzeugung",type:"bar",barMaxWidth:15,
      itemStyle:{color:theme.compareActual},
      data:rows.map(x=>valueOrNull(x.ist_wh)===null?null:Number((x.ist_wh/1000).toFixed(3)))},
  ];
  opt.tooltip.formatter=params=>{
    if(!params?.length)return "";
    const row=rows[params[0].dataIndex];
    return label(row.zeit,data.zeitzone)+"\n"+
      "Prognose: "+(valueOrNull(row.prognose_wh)===null?"–":fmt(row.prognose_wh/1000))+" kWh\n"+
      "Ist: "+(valueOrNull(row.ist_wh)===null?"–":fmt(row.ist_wh/1000))+" kWh";
  };
  return {options:opt,rows,width:Math.max(640,rows.length*45)};
}

export class SEPChartController {
  constructor() {
    this.charts=new Map();
    this.observer=typeof ResizeObserver==="function"
      ? new ResizeObserver(entries=>{
        for(const entry of entries){
          const item=[...this.charts.values()].find(x=>x.host===entry.target);
          if(item) item.chart.resize();
        }
      }) : null;
  }

  async paint(host,kind,chartData,onHourClick) {
    if(!host || !chartData)return false;
    const echarts=await loadVendorECharts();
    if(!host.isConnected)return false;
    const wrapper=host.closest(".sep-echarts-wrap");
    if(wrapper)wrapper.classList.add("chart-ready");
    host.style.width=Math.max(chartData.width, host.parentElement?.clientWidth || 0)+"px";
    host.classList.add("ready");
    let entry=this.charts.get(kind);
    if(entry && entry.host!==host){this.dispose(kind);entry=null;}
    if(!entry){
      const chart=echarts.init(host,null,{renderer:"svg"});
      entry={chart,host,signature:null};
      this.charts.set(kind,entry);
      if(this.observer)this.observer.observe(host);
    }
    const signature=JSON.stringify(chartData.options.series.map(x=>x.data))+
      JSON.stringify(chartData.options.xAxis.data)+
      JSON.stringify(chartData.options.yAxis)+
      JSON.stringify(chartData.options.textStyle)+
      JSON.stringify(chartData.options.series.map(x=>[x.itemStyle,x.lineStyle]));
    if(entry.signature!==signature){
      entry.chart.setOption(chartData.options,{notMerge:true,lazyUpdate:false});
      entry.signature=signature;
    }
    entry.chart.off("click");
    if(typeof onHourClick==="function"){
      entry.chart.on("click",p=>{
        const row=chartData.rows[p?.dataIndex];
        if(row) onHourClick(row);
      });
    }
    return true;
  }

  dispose(kind) {
    const entry=this.charts.get(kind);
    if(!entry)return;
    if(this.observer)this.observer.unobserve(entry.host);
    entry.chart.dispose();
    this.charts.delete(kind);
  }

  cleanup(activeKinds) {
    for(const kind of [...this.charts.keys()])
      if(!activeKinds.has(kind))this.dispose(kind);
  }

  destroy() {
    this.cleanup(new Set());
    if(this.observer)this.observer.disconnect();
  }
}
