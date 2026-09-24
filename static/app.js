'use strict';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let voices = [], selected = 'en-US-AndrewNeural', speed = .8, gender = 'all', jobs = [], paused = false, seen = null, toastTimer, previewBusy = false, retryEditId = null;
const names = new Intl.DisplayNames(['en'], {type:'language'});
const shortName = v => v.replace(/^[a-z]{2,3}-[A-Z]{2}-/, '').replace(/Neural$/, '').replace('Multilingual', ' Multilingual');
const duration = sec => `${Math.floor(Math.round(sec)/60)}:${String(Math.round(sec)%60).padStart(2,'0')}`;
const notice = text => { $('#toast').textContent = text; $('#toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').hidden = true, 5500); };
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {cache:'no-store'} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  let result; try { result = await response.json(); } catch { throw Error(`Request failed (${response.status}).`); }
  if (!response.ok) throw Error(result.error || `Request failed (${response.status}).`);
  return result;
}
function settings() { return {voice:selected, speed, pitch:Number($('#pitch').value), volume:Number($('#volume').value)}; }
function saveDraft() { try { localStorage.setItem('stillwater-draft', JSON.stringify({...settings(),text:$('#script').value,title:$('#title').value,batch:$('#batch').checked,autoplay:$('#autoplay').checked})); } catch {} }
function stats() {
  const text = $('#script').value.trim(), words = text ? text.split(/\s+/).length : 0;
  const count = scripts().length;
  $('#word-count').textContent = `${words.toLocaleString()} words · ~${duration(words/(150*speed)*60)} audio${$('#batch').checked ? ` · ${count} scripts` : ''}`;
  $('#batch-help').hidden = !$('#batch').checked;
  $('#generate').textContent = retryEditId ? '↻ Save changes & retry this script' : ($('#batch').checked && count > 1 ? `＋ Add ${count} scripts to queue` : '＋ Add to generation queue');
  saveDraft();
}
function updateControls() {
  document.querySelectorAll('[data-speed]').forEach(b => { b.classList.toggle('active', Number(b.dataset.speed) === speed); b.setAttribute('aria-pressed', Number(b.dataset.speed) === speed); });
  $('#speed-note').textContent = `${speed <= .7 ? 'Slow & spacious' : speed < 1 ? 'Unhurried' : 'Natural pace'} · ${speed.toFixed(1)}×`;
  $('#pitch-value').textContent = `${Number($('#pitch').value)>0?'+':''}${$('#pitch').value} Hz`;
  $('#volume-value').textContent = `${Number($('#volume').value)>0?'+':''}${$('#volume').value}%`;
  $('#selected-voice').textContent = `${shortName(selected)} · ${speed.toFixed(1)}×`;
  stats();
}
function renderVoices() {
  const query = $('#voice-search').value.toLowerCase(), locale = $('#locale').value;
  const filtered = voices.filter(v => (!locale || v.Locale === locale) && (gender === 'all' || v.Gender === gender) && JSON.stringify(v).toLowerCase().includes(query));
  $('#voice-count').textContent = filtered.length;
  $('#voice-list').innerHTML = filtered.map(v => `<div class="voice-card ${selected===v.ShortName?'selected':''}"><button class="voice-select" data-voice="${esc(v.ShortName)}" aria-pressed="${selected===v.ShortName}"><span class="avatar">${esc(shortName(v.ShortName)[0])}</span><span><span class="voice-name">${esc(shortName(v.ShortName))}</span><span class="voice-details">${esc(v.Gender)} · ${esc((v.VoiceTag?.VoicePersonalities || []).slice(0,2).join(', ') || v.Locale)}${locale?'':' · '+esc(v.Locale)}</span></span></button><button class="play-voice" data-preview="${esc(v.ShortName)}" title="Preview ${esc(shortName(v.ShortName))}" aria-label="Preview ${esc(shortName(v.ShortName))}" ${previewBusy?'disabled':''}>▶</button></div>`).join('') || '<p class="muted">No matching voices. Try another filter.</p>';
  $('#selected-voice').textContent = `${shortName(selected)} · ${speed.toFixed(1)}×`;
}
async function loadVoices(refresh=false) {
  const result = await api(refresh ? '/api/voices/refresh' : '/api/voices', refresh ? {} : undefined);
  voices = result.voices;
  const locales = [...new Set(voices.map(v => v.Locale))].sort((a,b) => (a==='en-US'?-1:b==='en-US'?1:a.localeCompare(b)));
  const previous = $('#locale').value;
  $('#locale').innerHTML = '<option value="">All languages & regions</option>' + locales.map(l => `<option value="${esc(l)}">${esc(voices.find(v=>v.Locale===l).LocaleName || names.of(l))}</option>`).join('');
  $('#locale').value = locales.includes(previous) ? previous : 'en-US';
  if (voices.length && !voices.some(v=>v.ShortName===selected)) selected = voices.find(v=>v.Locale==='en-US')?.ShortName || voices[0].ShortName;
  $('#banner').hidden = !result.warning; $('#banner').textContent = result.warning;
  $('#connection').textContent = voices.length ? `● ${voices.length} voices connected` : 'No voices available';
  renderVoices(); updateControls();
}
function scripts() { return ($('#batch').checked ? $('#script').value.split(/^\s*---\s*$/m) : [$('#script').value]).map(t=>t.trim()).filter(Boolean); }
async function submit() {
  const texts = scripts();
  if (!texts.length) return notice('Paste your script first.');
  if (!selected || !voices.length) return notice('Wait for the voice list, or refresh voices.');
  const title = $('#title').value.trim();
  const items = texts.map((text,i)=>({...settings(),text,title:title ? title+(texts.length>1?` · ${i+1}`:'') : ''}));
  $('#generate').disabled = true;
  try {
    if (retryEditId) { if(items.length!==1) throw Error('Edit one failed script at a time. Turn off Batch mode.'); await api(`/api/jobs/${retryEditId}`, {action:'retry',job:items[0]}); retryEditId=null; notice('Changes saved. This script will retry in its original position.'); }
    else { await api('/api/jobs', {jobs:items}); notice(`${items.length} script${items.length>1?'s':''} added to the queue.`); }
    $('#script').value=''; $('#title').value=''; stats(); await poll();
  } catch(e) {notice(e.message);} finally {$('#generate').disabled=false;}
}
function jobHTML(job) {
  const active = ['queued','running','retrying'].includes(job.status);
  const label = {queued:'Waiting', running:'Generating', retrying:'Retrying', completed:'Ready', cancelled:'Cancelled'}[job.status];
  return `<div class="job-top"><h3>${esc(job.title)}</h3><span class="status">${label}</span></div><p class="job-meta">${esc(shortName(job.voice))} · ${job.speed.toFixed(1)}× · ${job.pitch>0?'+':''}${job.pitch} Hz${job.duration?' · '+duration(job.duration):''}</p><p class="job-script">${esc(job.text)}</p>${job.status==='running'?`<div class="progress"><div style="width:${Math.max(3,job.progress*100)}%"></div></div><p class="job-meta">Generating · ${Math.round(job.progress*100)}% · attempt ${job.attempts}</p>`:''}${job.status==='retrying'?`<p class="job-error">${esc(job.error)}</p><p class="retry-countdown">Retry in ${Math.max(0,Math.ceil(job.next_retry-Date.now()/1000))}s · attempt ${job.attempts}. Later scripts are waiting.</p>`:''}${job.status==='completed'?`<audio controls preload="metadata" src="/files/${job.id}.mp3"></audio><div class="downloads"><a href="/files/${job.id}.mp3?download=1" download>↓ MP3 audio</a><a href="/files/${job.id}.vtt?download=1" download>↓ VTT</a><a href="/files/${job.id}.srt?download=1" download>↓ SRT</a></div>`:''}<div class="job-actions">${job.status==='retrying'?'<button data-action="retry">Retry now</button><button data-action="edit">Edit & fix</button>':''}${active?'<button class="cancel" data-action="cancel">Cancel script</button>':'<button data-action="reuse">Use script again</button>'}</div>`;
}
function renderJobs() {
  const pending = jobs.filter(j=>['queued','running','retrying'].includes(j.status));
  $('#queue-count').textContent = `${jobs.filter(j=>j.status==='completed').length} ready`;
  $('#queue-status').textContent = paused ? 'Ⅱ Paused after current script' : pending.some(j=>j.status==='retrying') ? '↻ Retrying first script' : pending.length ? `${pending.length} in queue` : '● Queue ready';
  $('#pause').textContent = paused ? 'Resume queue' : 'Pause queue';
  if (!jobs.length) return;
  $('#jobs .empty')?.remove();
  const ordered = [...pending, ...jobs.filter(j=>!pending.includes(j)).reverse()];
  ordered.forEach((job,i)=>{
    let node = document.getElementById(`job-${job.id}`);
    if (!node) {node=document.createElement('article');node.id=`job-${job.id}`;node.dataset.id=job.id;}
    // Preserve audio elements across polling so playback is never reset.
    const signature = JSON.stringify([job.status,job.progress,job.attempts,job.title,job.voice,job.error]);
    if (node.dataset.signature!==signature) {node.className=`job ${job.status}`;node.innerHTML=jobHTML(job);node.dataset.signature=signature;}
    if(job.status==='retrying') node.querySelector('.retry-countdown').textContent = `${paused?'Queue paused.':`Retry in ${Math.max(0,Math.ceil(job.next_retry-Date.now()/1000))}s.`} Attempt ${job.attempts}. Later scripts are waiting.`;
    const current=$('#jobs').children[i]; if(current!==node) $('#jobs').insertBefore(node,current||null);
  });
}
let polling = false;
async function poll() {
  if(polling) return; polling=true;
  try {
    const state=await api('/api/state'); jobs=state.jobs;paused=state.paused;renderJobs();
    const completed=new Set(jobs.filter(j=>j.status==='completed').map(j=>j.id));
    if(seen && $('#autoplay').checked) {const fresh=[...completed].find(id=>!seen.has(id)); if(fresh && ![...document.querySelectorAll('audio')].some(a=>!a.paused)) {const player=$(`#job-${fresh} audio`);player?.play().catch(()=>notice('Your recording is ready. Press play to listen.'));}}
    seen=completed;
    if(voices.length) $('#connection').textContent=`● ${voices.length} voices connected`;
  } catch(e) {$('#connection').textContent='Disconnected · reconnecting…';} finally {polling=false;}
}
$('#voice-list').addEventListener('click', async e=>{
  const choose=e.target.closest('[data-voice]'), preview=e.target.closest('[data-preview]');
  if(choose){selected=choose.dataset.voice;renderVoices();saveDraft();}
  if(preview && !previewBusy){
    const voice=preview.dataset.preview; selected=voice;previewBusy=true;renderVoices();saveDraft();
    $('#preview-label').textContent=`Preparing ${shortName(voice)} at ${speed.toFixed(1)}×…`;
    try {const result=await api('/api/preview',{...settings(),voice});$('#preview-player').src=result.url;$('#preview-player').hidden=false;$('#preview-label').textContent=`${shortName(voice)} · voice preview`;await $('#preview-player').play().catch(e=>{if(e.name!=='AbortError')notice('Preview ready. Press play to listen.');});}
    catch(e){$('#preview-label').textContent='Preview unavailable. Try again.';notice(e.message);}
    finally{previewBusy=false;renderVoices();}
  }
});
$('#gender').addEventListener('click',e=>{const b=e.target.closest('[data-value]');if(!b)return;gender=b.dataset.value;$('#gender').querySelectorAll('button').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',x===b);});renderVoices();});
$('#locale').onchange=renderVoices;$('#voice-search').oninput=renderVoices;
$('#refresh-voices').onclick=async()=>{const b=$('#refresh-voices');b.disabled=true;try{await loadVoices(true);notice('Voice list refreshed.');}catch(e){notice(e.message);}finally{b.disabled=false;}};
$('#speeds').onclick=e=>{const b=e.target.closest('[data-speed]');if(b){speed=Number(b.dataset.speed);updateControls();}};
['pitch','volume'].forEach(id=>$('#'+id).oninput=updateControls);
['script','title','batch','autoplay'].forEach(id=>$('#'+id).addEventListener('input',stats));
document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>{
  const presets={deep:['en-US-ChristopherNeural',.8,-12],warm:['en-US-AndrewNeural',.9,-5],soft:['en-US-JennyNeural',.8,-3]};
  const values=presets[b.dataset.preset];if(!voices.some(v=>v.ShortName===values[0])) return notice('This preset voice is unavailable. Refresh the voice list.');
  [selected,speed]=values;$('#pitch').value=values[2];$('#volume').value=0;$('#locale').value='en-US';$('#voice-search').value='';gender='all';$('#gender button[data-value="all"]').click();updateControls();renderVoices();notice(`${b.textContent} preset applied. Preview the voice to hear it.`);
});
$('#generate').onclick=submit;
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'&&!$('#generate').disabled){e.preventDefault();submit();}});
$('#pause').onclick=async()=>{try{await api('/api/queue',{paused:!paused});await poll();}catch(e){notice(e.message);}};
$('#jobs').onclick=async e=>{
  const b=e.target.closest('[data-action]');if(!b)return;
  const job=jobs.find(j=>j.id===b.closest('.job').dataset.id);if(!job)return;
  const action=b.dataset.action;
  if(action==='reuse'||action==='edit'){
    if($('#script').value.trim()&&!confirm('Replace the current draft with this script?'))return;
    retryEditId=action==='edit'?job.id:null;
    if(action==='edit') {try{await api('/api/queue',{paused:true});}catch(e){return notice(e.message);}notice('Queue paused while you fix this script. Save it, then resume the queue.');}
    $('#script').value=job.text;$('#title').value=job.title;selected=job.voice;speed=job.speed;$('#pitch').value=job.pitch;$('#volume').value=job.volume;$('#batch').checked=false;updateControls();renderVoices();$('#script').focus();return;
  }
  b.disabled=true;try{await api(`/api/jobs/${job.id}`,{action});await poll();}catch(e){notice(e.message);}finally{b.disabled=false;}
};
$('#import-button').onclick=()=>$('#import-files').click();
$('#import-files').onchange=async e=>{
  const files=[...e.target.files];if(!files.length)return;
  if(files.length>50||files.some(f=>f.size>160000)){notice('Import up to 50 text files, each under 160 KB.');e.target.value='';return;}
  const texts=await Promise.all(files.map(f=>f.text()));
  const existing=$('#script').value.trim();$('#script').value=[existing,...texts].filter(Boolean).join('\n\n---\n\n');
  $('#batch').checked=files.length>1||Boolean(existing);if(!existing&&files.length===1)$('#title').value=files[0].name.replace(/\.txt$/i,'');stats();e.target.value='';notice(`${files.length} text file${files.length>1?'s':''} imported. Review and add to the queue.`);
};
$('#theme').onclick=()=>{document.body.classList.toggle('dark');try{localStorage.setItem('stillwater-theme',document.body.classList.contains('dark')?'dark':'light');}catch{}};
document.addEventListener('play',e=>{if(e.target.tagName==='AUDIO')document.querySelectorAll('audio').forEach(a=>{if(a!==e.target)a.pause();});},true);
try{if(localStorage.getItem('stillwater-theme')==='dark')document.body.classList.add('dark');const draft=JSON.parse(localStorage.getItem('stillwater-draft')||'null');if(draft){selected=draft.voice||selected;speed=[.5,.6,.7,.8,.9,1].includes(draft.speed)?draft.speed:.8;$('#pitch').value=draft.pitch??-5;$('#volume').value=draft.volume??0;$('#script').value=draft.text||'';$('#title').value=draft.title||'';$('#batch').checked=!!draft.batch;$('#autoplay').checked=draft.autoplay!==false;}}catch{}
updateControls();loadVoices().catch(e=>{notice(e.message);$('#connection').textContent='Could not load voices';});poll();setInterval(poll,1200);
