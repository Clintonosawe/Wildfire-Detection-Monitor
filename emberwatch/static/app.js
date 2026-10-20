'use strict';
let incidents = [], selected = null;
const $ = id => document.getElementById(id);
const transitions = {new:['reviewing'],reviewing:['confirmed','dismissed'],confirmed:['resolved'],dismissed:['reviewing'],resolved:['reviewing']};
function el(tag, text, cls) { const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(cls)e.className=cls; return e; }
async function load() {
 try {const response=await fetch('/api/incidents');if(!response.ok)throw new Error('Could not load incidents');incidents=await response.json();if(!incidents.some(d=>d.id===selected))selected=incidents[0]?.id;render();$('message').textContent='';}
 catch(e){$('message').textContent=e.message;}
}
function render(){
 $('stats').replaceChildren();
 const active=incidents.filter(d=>!['resolved','dismissed'].includes(d.status));
 for(const [label,value] of [['Total incidents',incidents.length],['High priority · active',active.filter(d=>d.band==='high').length],['Awaiting review',incidents.filter(d=>d.status==='new').length],['Observations',incidents.reduce((s,d)=>s+d.count,0)]]){const box=el('div',undefined,'stat');box.append(el('span',label),el('strong',value));$('stats').append(box);}
 const visible=incidents.filter(d=>$('filter').value==='all'||d.status===$('filter').value);
 if(!visible.some(d=>d.id===selected))selected=visible[0]?.id;
 $('list').replaceChildren();
 for(const d of visible){const b=el('button',undefined,'incident'+(d.id===selected?' active':''));b.setAttribute('aria-pressed',String(d.id===selected));b.append(el('span',`${d.band} priority · ${d.score}/100`,'badge '+d.band),el('strong',`EW-${d.id.slice(0,6).toUpperCase()}`),el('small',`${d.count} observations · ${d.status} · ${d.source}`));b.onclick=()=>{selected=d.id;render();};$('list').append(b);}
 if(!visible.length)$('list').append(el('p','No incidents match this view. Run the demo command to load sample data.'));
 plot(visible);detail(visible.find(d=>d.id===selected));
}
function plot(rows){
 const svg=$('plot');svg.replaceChildren();if(!rows.length)return;
 const minX=Math.min(...rows.map(d=>d.longitude))-0.5,maxX=Math.max(...rows.map(d=>d.longitude))+0.5,minY=Math.min(...rows.map(d=>d.latitude))-0.3,maxY=Math.max(...rows.map(d=>d.latitude))+0.3;
 function shape(tag,attrs,text){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text)e.textContent=text;svg.append(e);return e;}
 for(let i=0;i<5;i++){const x=50+i*155,y=20+i*48;shape('line',{x1:x,x2:x,y1:20,y2:212,stroke:'#203343'});shape('line',{x1:50,x2:670,y1:y,y2:y,stroke:'#203343'});shape('text',{x:x-16,y:237},(minX+(maxX-minX)*i/4).toFixed(1)+'°');shape('text',{x:4,y:y+4},(maxY-(maxY-minY)*i/4).toFixed(1)+'°');}
 for(const d of rows){const c=shape('circle',{cx:50+(d.longitude-minX)/(maxX-minX)*620,cy:20+(maxY-d.latitude)/(maxY-minY)*192,r:d.id===selected?12:8,fill:{high:'#ff9266',medium:'#dfbe68',low:'#77bcb5'}[d.band]});const title=document.createElementNS(svg.namespaceURI,'title');title.textContent=`${d.id}: ${d.score}/100`;c.append(title);c.onclick=()=>{selected=d.id;render();};}
}
function detail(d){
 const root=$('detail');root.replaceChildren();if(!d)return;
 root.append(el('h3',`EW-${d.id.slice(0,6).toUpperCase()}`),el('p',`${d.source} · ${d.status.toUpperCase()} · ${d.latitude.toFixed(3)}, ${d.longitude.toFixed(3)}`,'meta'),el('p',`Latest observation: ${d.latest} · ${d.count} detections. Score uses the highest-priority observation, not a sum.`,'meta'));
 const parts=el('div',undefined,'components');for(const [key,value]of Object.entries(d.components)){const c=el('div',key.replaceAll('_',' '),'component');c.append(el('strong','+'+value));parts.append(c);}root.append(parts);
 if(d.missing_weather)root.append(el('p','Weather is incomplete for the scored observation; missing contributions are zero.','meta'));
 root.append(el('h2','Record a review'));
 const form=el('form',undefined,'review'), select=el('select'),note=el('textarea'),submit=el('button','Save decision','primary');select.setAttribute('aria-label','Review action');note.setAttribute('aria-label','Evidence or decision note');note.placeholder='Add evidence and explain your decision…';note.required=true;note.minLength=3;note.maxLength=1000;
 for(const action of [...transitions[d.status],'report']){const option=el('option',action==='report'?'Add unverified report':`Move to ${action}`);option.value=action;select.append(option);}submit.type='submit';form.append(note,select,submit);
 form.onsubmit=async event=>{event.preventDefault();submit.disabled=true;try{const res=await fetch('/api/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:d.id,action:select.value,note:note.value})});const result=await res.json();if(!res.ok)throw new Error(result.error);await load();$('message').textContent='Review saved.';}catch(e){$('message').textContent=e.message;}finally{submit.disabled=false;}};
 root.append(form,el('h2','Evidence timeline'));const timeline=el('ul',undefined,'events');for(const e of d.events){const li=el('li');li.append(el('small',`${e.created} · ${e.kind}`),el('span',e.detail));timeline.append(li);}root.append(timeline);
}
$('filter').onchange=render;$('refresh').onclick=load;load();
