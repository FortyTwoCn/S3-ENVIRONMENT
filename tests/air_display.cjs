const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
class Element{constructor(){this.textContent='';this.children=[];}append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=nodes;}}
const elements=new Map();const document={getElementById(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement(){return new Element();}};
const source=fs.readFileSync(path.join(__dirname,'../server/public/assets/app.js'),'utf8');
const context=vm.createContext({document,console});vm.runInContext(source.slice(0,source.indexOf('async function loadHistory()')),context);
function render(data){context.input=data;vm.runInContext("state.id='d';state.devices=[{id:'d',online:true,config:{mq_enabled:false},latest:{data:input}}];renderLatest();",context);return elements.get('air-metrics').children;}
let cards=render({});assert.equal(cards.length,6);for(const card of cards)assert.equal(card.children[1].textContent,'--');
cards=render({eco2_ppm:823.5,bvoc_ppm:.672,iaq:76.2,static_iaq:81.4,gas_percentage:63.8,compensated_gas:10.93,raw_temperature_c:26.82,raw_humidity_pct:44.3});
assert.equal(cards[0].children[0].textContent,'CO₂ 等效估计');assert.equal(cards[0].children[1].children[0].textContent,'ppm');
assert.equal(cards[1].children[1].textContent,Number(.672).toLocaleString('zh-CN',{maximumFractionDigits:3}));
assert.equal(cards[4].children[2].textContent,'相对基线 · 不代表气体浓度');assert.equal(cards[5].children[1].children[0].textContent,'');
assert(elements.get('air-raw').textContent.includes('26.82'));assert(!elements.get('air-raw').textContent.includes('校准'));
cards=render({eco2_ppm:null,iaq:null});assert.equal(cards[0].children[1].textContent,'--');assert.equal(cards[2].children[1].textContent,'--');
console.log(JSON.stringify({status:'PASS',checks:16,scope:'estimated units, missing/legacy values, gas percentage meaning, no status cards'}));
