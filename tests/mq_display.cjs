const fs=require('fs');
const vm=require('vm');
const assert=require('assert/strict');
const path=require('path');
class Element {
  constructor(tag='div'){this.tag=tag;this.textContent='';this.children=[];this.hidden=false;}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
}
const elements=new Map();
const document={getElementById(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement(tag){return new Element(tag);}};
const source=fs.readFileSync(process.argv[2]||path.join(__dirname,'../server/public/assets/app.js'),'utf8');
const prefix=source.slice(0,source.indexOf('async function loadHistory()'));
const context=vm.createContext({document,console});
vm.runInContext(prefix,context);
function run(configEnabled,sampleEnabled,voltage=2891){
  context.configEnabled=configEnabled;context.sampleEnabled=sampleEnabled;context.voltage=voltage;
  vm.runInContext("state.id='device';state.devices=[{id:'device',online:true,config:{mq_enabled:configEnabled,report_interval_s:300},latest:{observed_at:'2026-10-05T00:00:00Z',clock_quality:'ntp',data:{mq_enabled:sampleEnabled,mq_adc_mv:voltage,mq_adc_raw:3572,mq_ao_v:5.7,mq_gpio:true,mq_ready:true,mq_smoke:true}}}];renderLatest();",context);
  const card=elements.get('metrics').children[6];
  return {value:card.children[1].textContent,unit:card.children[1].children[0].textContent,diagnostics:elements.get('diagnostics').textContent,bannerHidden:elements.get('smoke-banner').hidden};
}
let r=run(false,undefined);assert.equal(r.value,'未启用');assert.equal(r.unit,'');assert(!r.diagnostics.includes('2891'));assert(!r.diagnostics.includes('HIGH'));assert(r.bannerHidden);
r=run(false,false,null);assert.equal(r.value,'未启用');assert(r.bannerHidden);
r=run(true,false,null);assert.equal(r.value,'等待采样');assert(r.bannerHidden);
r=run(true,true,1012);assert.equal(r.value,Number(1012).toLocaleString('zh-CN'));assert.equal(r.unit,'mV');assert(r.diagnostics.includes('HIGH'));assert(!r.bannerHidden);
r=run(true,undefined,1012);assert.equal(r.unit,'mV');assert(!r.bannerHidden);
console.log(JSON.stringify({status:'PASS',checks:5,regression:'disabled MQ hides floating ADC and GPIO; enabled/legacy devices still show readings'}));
