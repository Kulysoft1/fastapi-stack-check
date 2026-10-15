// app/static/app.js
(function(){
'use strict';
const pgPill=document.getElementById('pg-pill'),redisPill=document.getElementById('redis-pill');
const pgStatus=pgPill.querySelector('.status'),redisStatus=redisPill.querySelector('.status');
const noteForm=document.getElementById('note-form'),noteTitle=document.getElementById('note-title'),noteBody=document.getElementById('note-body'),notesList=document.getElementById('notes-list');
const kvForm=document.getElementById('kv-form'),kvKey=document.getElementById('kv-key'),kvValue=document.getElementById('kv-value'),kvTtl=document.getElementById('kv-ttl'),kvList=document.getElementById('kv-list');
let pgOk=false,redisOk=false;
function toast(m){const e=document.querySelector('.error-toast');if(e)e.remove();const t=document.createElement('div');t.className='error-toast';t.textContent=m;document.body.appendChild(t);setTimeout(()=>t.remove(),4000)}
function setPill(el,statusEl,ok,info){statusEl.textContent=ok?'ok':'down';statusEl.classList.remove('ok','down');statusEl.classList.add(ok?'ok':'down');el.title=info?(info.error||(info.latency_ms!=null?info.latency_ms+' ms':'')):''}
async function j(u,o={}){const r=await fetch(u,{...o,headers:{'Content-Type':'application/json',...(o.headers||{})}});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error((typeof d.detail==='string'?d.detail:JSON.stringify(d.detail))||`HTTP ${r.status}`);return d}
const esc=s=>{const d=document.createElement('div');d.textContent=s;return d.innerHTML};
const when=s=>new Date(s).toLocaleString(undefined,{year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
const ttlLeft=s=>s==null?'no expiry':s<60?`${s}s`:s<3600?`${Math.floor(s/60)}m ${s%60}s`:`${Math.floor(s/3600)}h ${Math.floor(s%3600/60)}m`;
async function checkHealth(){try{const r=await fetch('/health/ready');const d=await r.json().catch(()=>({}));const sv=d.services||[];const pg=sv.find(s=>s.service==='postgres')||{},rd=sv.find(s=>s.service==='redis')||{};pgOk=pg.status==='ok';redisOk=rd.status==='ok';setPill(pgPill,pgStatus,pgOk,pg);setPill(redisPill,redisStatus,redisOk,rd)}catch(err){pgOk=redisOk=false;setPill(pgPill,pgStatus,false);setPill(redisPill,redisStatus,false)}}
async function loadNotes(){try{const d=await j('/api/notes');renderNotes(d)}catch(e){if(pgOk)toast('Failed to load notes: '+e.message);notesList.innerHTML='<div class="empty">Failed to load notes</div>'}}
function renderNotes(n){if(!n.length){notesList.innerHTML='<div class="empty">No notes yet. Add one above.</div>';return}
notesList.innerHTML=n.map(x=>`<div class="item">
<div class="title">${esc(x.title)}<span>${when(x.created_at)}</span></div>
<div class="body">${esc(x.body)}</div>
<div class="actions"><button class="btn danger" data-del-note="${x.id}">×</button></div>
</div>`).join('')}
async function createNote(t,b){await j('/api/notes',{method:'POST',body:JSON.stringify({title:t,body:b})})}
async function delNote(id){await j(`/api/notes/${id}`,{method:'DELETE'})}
noteForm.addEventListener('submit',async e=>{
e.preventDefault();const t=noteTitle.value.trim(),b=noteBody.value.trim();if(!t||!b)return;const btn=noteForm.querySelector('button');btn.disabled=true;
try{await createNote(t,b);noteForm.reset();await loadNotes()}catch(e){toast('Failed to create note: '+e.message)}finally{btn.disabled=false}});
notesList.addEventListener('click',async e=>{
const b=e.target.closest('[data-del-note]');if(!b)return;const id=parseInt(b.dataset.delNote,10);b.disabled=true;
try{await delNote(id);await loadNotes()}catch(e){toast('Failed to delete note: '+e.message);b.disabled=false}});
async function loadKeys(){try{const d=await j('/api/kv');renderKeys(d.keys||[])}catch(e){if(redisOk)toast('Failed to load keys: '+e.message);kvList.innerHTML='<div class="empty">Failed to load keys</div>'}}
function renderKeys(k){if(!k.length){kvList.innerHTML='<div class="empty">No keys yet. Set one above.</div>';return}
kvList.innerHTML=k.map(x=>`<div class="item">
<div class="kv"><span class="k">${esc(x.key)}</span><span class="v">${esc(x.value)}</span><span class="ttl">TTL: ${ttlLeft(x.ttl)}</span></div>
<div class="actions"><button class="btn danger" data-del-kv="${esc(x.key)}">×</button></div>
</div>`).join('')}
async function setKey(k,v,t){const b={value:v};if(t)b.ttl=t;await j(`/api/kv/${encodeURIComponent(k)}`,{method:'PUT',body:JSON.stringify(b)})}
async function delKey(k){await j(`/api/kv/${encodeURIComponent(k)}`,{method:'DELETE'})}
kvForm.addEventListener('submit',async e=>{
e.preventDefault();const k=kvKey.value.trim(),v=kvValue.value.trim(),t=kvTtl.value?parseInt(kvTtl.value,10):null;if(!k||!v)return;const btn=kvForm.querySelector('button');btn.disabled=true;
try{await setKey(k,v,t);kvForm.reset();await loadKeys()}catch(e){toast('Failed to set key: '+e.message)}finally{btn.disabled=false}});
kvList.addEventListener('click',async e=>{
const b=e.target.closest('[data-del-kv]');if(!b)return;const k=b.dataset.delKv;b.disabled=true;
try{await delKey(k);await loadKeys()}catch(e){toast('Failed to delete key: '+e.message);b.disabled=false}});
async function init(){await checkHealth();await Promise.all([loadNotes(),loadKeys()]);setInterval(checkHealth,5000)}
document.readyState==='loading'?document.addEventListener('DOMContentLoaded',init):init();
})();