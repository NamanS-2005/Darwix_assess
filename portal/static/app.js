/* Darwix assessment portal – vanilla JS single-page app (hash routing, no build step). */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const md = t => DOMPurify.sanitize(marked.parse(t || ''));
async function api(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return (r.headers.get('content-type') || '').includes('json') ? r.json() : r.text();
}
const MARKET_LABEL = { in_lender: 'Udaan Credit (India · EN)', ph_life: 'Bituin Life (Philippines · Taglish)', id_multifinance: 'Pundi Mitra (Indonesia · Bahasa)' };
const DISP_GOOD = /PTP|AUTO_DEBIT|ALREADY_PAID|ESCALATED|HARDSHIP|CALLBACK|WRONG_PARTY|VERIFICATION_FAILED/;

/* ---------------- shell ---------------- */
let cleanups = [];
function onLeave(fn) { cleanups.push(fn); }
function leave() { cleanups.forEach(f => { try { f(); } catch (e) { } }); cleanups = []; }

const THEME_KEY = 'darwix-theme';
try { const t = localStorage.getItem(THEME_KEY); if (t) document.documentElement.dataset.theme = t; } catch (e) { }
$('#theme').onclick = () => {
  const dark = matchMedia('(prefers-color-scheme: dark)').matches;
  const cur = document.documentElement.dataset.theme || (dark ? 'dark' : 'light');
  const next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem(THEME_KEY, next); } catch (e) { }
};
$('#menu').onclick = () => $('#side').classList.toggle('open');

function openDrawer(title, html) {
  $('#drawer-title').textContent = title;
  $('#drawer-body').innerHTML = html;
  $('#drawer').classList.add('open'); $('#drawer-bg').classList.add('on');
}
function closeDrawer() {
  $('#drawer').classList.remove('open'); $('#drawer-bg').classList.remove('on');
  $$('#drawer-body audio').forEach(a => a.pause());
}
$('#drawer-close').onclick = closeDrawer; $('#drawer-bg').onclick = closeDrawer;
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDrawer(); });

const tip = $('#tip');
function showTip(e, html) { tip.innerHTML = html; tip.style.opacity = 1; tip.style.left = Math.min(e.clientX + 12, innerWidth - 290) + 'px'; tip.style.top = (e.clientY + 12) + 'px'; }
function hideTip() { tip.style.opacity = 0; }

async function loadStatus() {
  try {
    const s = await api('/api/status');
    $('#sysstatus').innerHTML = `<div>LLM: ${s.providers.length ? esc(s.providers.join(' → ')) : '<b style="color:var(--bad)">not configured</b>'}</div>
      <div>ASR: ${s.asr ? 'Groq Whisper' : 'off'} · KB ${esc(s.retrieval)}</div><div class="mono">${esc(s.kb_version)}</div>`;
  } catch (e) { $('#sysstatus').textContent = 'Server unreachable'; }
}

function tabs(el, items, current, onPick) {
  el.innerHTML = items.map(([k, label]) => `<button data-k="${k}" class="${k === current ? 'on' : ''}">${esc(label)}</button>`).join('');
  $$('button', el).forEach(b => b.onclick = () => onPick(b.dataset.k));
}
function pageHead(eyebrow, title, desc, right = '') {
  return `<div class="page-head"><div><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1>${desc ? `<p>${desc}</p>` : ''}</div>${right}</div>`;
}
async function mdInto(el, key) {
  el.innerHTML = '<div class="loading">Loading…</div>';
  try { el.innerHTML = `<div class="md">${md(await api('/api/doc/' + key))}</div>`; renderMermaid(el); }
  catch (e) { el.innerHTML = `<div class="empty">Not available yet (${esc(e.message.slice(0, 80))})</div>`; }
}
let mermaidMod;
async function renderMermaid(el) {
  const blocks = $$('pre code.language-mermaid', el);
  if (!blocks.length) return;
  try {
    mermaidMod = mermaidMod || (await import('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs')).default;
    const dark = getComputedStyle(document.documentElement).colorScheme === 'dark';
    mermaidMod.initialize({ startOnLoad: false, theme: dark ? 'dark' : 'neutral', securityLevel: 'strict',
      flowchart: { useMaxWidth: false, nodeSpacing: 30, rankSpacing: 40 }, themeVariables: { fontSize: '15px' } });
    for (const [i, b] of blocks.entries()) {
      const { svg } = await mermaidMod.render('mm' + Date.now() + i, b.textContent);
      const div = document.createElement('div'); div.className = 'card'; div.style.overflow = 'auto'; div.innerHTML = svg;
      const s = div.querySelector('svg'); if (s) { s.style.maxWidth = 'none'; s.style.height = 'auto'; }
      const hint = document.createElement('div'); hint.className = 'small muted'; hint.textContent = 'Scroll sideways to see the whole diagram.'; div.prepend(hint);
      b.parentElement.replaceWith(div);
    }
  } catch (e) { /* leave the code block visible */ }
}

/* ---------------- chart: horizontal grouped bars ---------------- */
function barChart(el, { rows, series, unit = '', labelW = 230, decimals = 1 }) {
  const barH = 14, gap = 4, groupGap = 14, padR = 64;
  const W = Math.max(360, Math.min(820, el.clientWidth || 720));
  const raw = Math.max(...rows.flatMap(r => series.map(s => r[s.key] ?? 0))) || 1;
  const mag = 10 ** Math.floor(Math.log10(raw / 4));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(st => raw / st <= 4) || 10 * mag;
  const max = Math.ceil(raw / step) * step;
  labelW = Math.min(labelW, W * 0.42);
  const groupH = series.length * barH + (series.length - 1) * gap;
  const H = rows.length * (groupH + groupGap);
  const x = v => (v / max) * (W - labelW - padR);
  let svg = `<svg width="${W}" height="${H + 22}" viewBox="0 0 ${W} ${H + 22}" role="img" style="max-width:100%">`;
  svg += '<g class="grid">';
  for (let v = 0; v <= max + 1e-9; v += step) { const xx = labelW + x(v); svg += `<line x1="${xx}" x2="${xx}" y1="0" y2="${H}"/><text class="lbl" x="${xx}" y="${H + 16}" text-anchor="middle">${+v.toFixed(2)}${unit}</text>`; }
  svg += '</g>';
  const maxChars = Math.floor(labelW / 7);
  rows.forEach((r, i) => {
    const y0 = i * (groupH + groupGap);
    svg += `<text class="lbl" x="${labelW - 10}" y="${y0 + groupH / 2 + 4}" text-anchor="end">${esc(r.label.length > maxChars ? r.label.slice(0, maxChars - 1) + '…' : r.label)}</text>`;
    series.forEach((s, j) => {
      const v = r[s.key]; if (v == null) return;
      const y = y0 + j * (barH + gap), w = Math.max(4, x(v));
      svg += `<g class="bar" data-tip="${esc(`<b>${r.label}</b><br>${s.name}: ${v.toFixed(decimals)}${unit}`)}">
        <rect x="${labelW - 4}" y="${y - 2}" width="${w + 54}" height="${barH + 4}" fill="transparent"/>
        <path d="M${labelW},${y} h${w - 4} a4,4 0 0 1 4,4 v${barH - 8} a4,4 0 0 1 -4,4 h${-(w - 4)} z" fill="var(${s.color})"/>
        <text class="val" x="${labelW + w + 6}" y="${y + barH - 3}">${v.toFixed(decimals)}${unit}</text></g>`;
    });
  });
  svg += '</svg>';
  el.innerHTML = (series.length > 1 ? `<div class="legend">${series.map(s => `<span><i style="background:var(${s.color})"></i>${esc(s.name)}</span>`).join('')}</div>` : '') + `<div class="chart">${svg}</div>`;
  $$('.bar', el).forEach(g => { g.onmousemove = e => showTip(e, g.dataset.tip); g.onmouseleave = hideTip; });
}

/* ---------------- shared: simulated call table ---------------- */
async function simTable(el, suite, title) {
  el.innerHTML = '<div class="loading">Loading…</div>';
  const rows = await api('/api/sims/' + suite);
  const passed = rows.filter(r => r.passed).length;
  el.innerHTML = `<div class="row" style="margin-bottom:10px"><h3>${esc(title)}</h3><span class="pill ${passed === rows.length ? 'good' : 'warn'}">${passed}/${rows.length} pass</span>
    <span class="muted small">Customer speech → neural TTS → Whisper ASR → agent. Click a row for transcript, checks and recording.</span></div>
    <div class="table-wrap"><table><thead><tr><th>Scenario</th><th>Result</th><th>Disposition</th><th class="num">Turns</th><th class="num">KB</th><th class="num">Guard</th><th class="num">ASR WER</th><th>Audio</th></tr></thead>
    <tbody>${rows.map((r, i) => `<tr class="click" data-i="${i}"><td>${esc(r.title)}</td>
      <td>${r.passed ? '<span class="pill good">✓ pass</span>' : '<span class="pill bad">✗ fail</span>'}</td>
      <td><span class="pill ${DISP_GOOD.test(r.disposition || '') ? 'accent' : 'warn'}">${esc(r.disposition || '—')}</span></td>
      <td class="num">${r.turns}</td><td class="num">${r.kb_lookups}</td><td class="num">${r.guard}</td>
      <td class="num">${r.asr_wer == null ? '—' : (r.asr_wer * 100).toFixed(1) + '%'}</td>
      <td>${r.has_audio ? '▶' : ''}</td></tr>`).join('')}</tbody></table></div>`;
  $$('tr.click', el).forEach(tr => tr.onclick = async () => {
    const r = rows[+tr.dataset.i];
    openDrawer(r.title, '<div class="loading">Loading transcript…</div>');
    const t = await api(`/files/sims/${suite}/${r.id}/transcript.md`).catch(() => 'Transcript not found');
    const models = Object.keys(r.providers || {}).map(k => k.split('/').slice(1).join('/'));
    $('#drawer-body').innerHTML = `
      ${r.has_audio ? `<audio controls src="/files/sims/${suite}/${r.id}/recording.mp3"></audio>` : ''}
      <div class="row mt">${r.passed ? '<span class="pill good">pass</span>' : '<span class="pill bad">fail</span>'}<span class="pill accent">${esc(r.disposition)}</span>
        ${models.map(m => `<span class="pill">${esc(m)}</span>`).join('')}</div>
      <h3 class="mt">Checks</h3><ul>${r.checks.map(([n, ok, note]) => `<li>${ok ? '✅' : '❌'} <b>${esc(n)}</b> — ${esc(note)}</li>`).join('')}</ul>
      <h3 class="mt">Transcript</h3><div class="md">${md(t.replace(/^# .*\n/, ''))}</div>`;
  });
}

/* ---------------- shared: live call panel (Q1 / Q3) ---------------- */
async function callPanel(el, marketIds) {
  const [mk, creds] = await Promise.all([api('/api/markets'), api('/api/test-customers')]);
  const markets = mk.markets.filter(m => marketIds.includes(m.id));
  el.innerHTML = `
  <div class="card" style="margin-bottom:14px"><div class="row">
    ${markets.length > 1 ? `<select id="c-market">${markets.map(m => `<option value="${m.id}">${esc(MARKET_LABEL[m.id] || m.company)}</option>`).join('')}</select>` : `<b>${esc(MARKET_LABEL[markets[0].id])}</b>`}
    <select id="c-cust"></select>
    <label class="row small" style="gap:6px"><input type="checkbox" id="c-mic" checked> microphone</label>
    <span class="spacer"></span>
    <button class="btn primary" id="c-start">Start call</button><button class="btn danger" id="c-end" disabled>End call</button>
  </div><div id="c-cred" class="small muted" style="margin-top:8px"></div></div>
  <div class="call">
    <div class="card">
      <div class="row"><span id="c-status" class="row small" style="gap:6px"><span class="status-dot"></span><span>idle</span></span><span class="spacer"></span><span class="small muted" id="c-callid"></span></div>
      <div class="log" id="c-log"><div class="empty">Pick a customer and start the call. The agent speaks first; answer with your voice or type below.</div></div>
      <div class="meter"><i id="c-meter"></i></div>
      <div class="row mt"><input type="text" id="c-text" placeholder="Type what the customer says and press Enter" disabled><button class="btn" id="c-send" disabled>Send</button></div>
    </div>
    <div class="grid" style="align-content:start">
      <div class="card"><h3>Call state</h3><dl class="kv" id="c-state"><dt>status</dt><dd>not started</dd></dl></div>
      <div class="card"><h3>Latency per turn (ms)</h3><div class="table-wrap"><table><thead><tr><th>#</th><th class="num">ASR</th><th class="num">Agent</th><th class="num">TTS</th></tr></thead><tbody id="c-lat"></tbody></table></div></div>
      <div class="card"><h3>Result</h3><div id="c-result" class="small muted">CRM summary, transcript and recording appear when the call ends.</div></div>
    </div>
  </div>`;
  const S = { callId: null, ended: false, turn: 0, mode: 'idle', stream: null, ctx: null, analyser: null, rec: null, chunks: [], speechMs: 0, silenceMs: 0, recStart: 0, timer: null, player: new Audio() };
  const VAD = { thr: 0.018, minSpeech: 250, endSilence: 900, maxUtt: 20000 };
  const marketSel = $('#c-market', el);
  const curMarket = () => marketSel ? marketSel.value : markets[0].id;
  function fillCustomers() {
    const m = markets.find(x => x.id === curMarket());
    $('#c-cust', el).innerHTML = m.customers.map(c => `<option value="${c.id}">${c.id} · ${esc(c.name)} · ${esc(c.product)}</option>`).join('');
    showCred();
  }
  function showCred() {
    const c = (creds[curMarket()] || []).find(x => x.id === $('#c-cust', el).value);
    $('#c-cred', el).innerHTML = c ? `Test identity (fictional mock CRM): DOB <b>${esc(c.dob)}</b> · account ends <b>${esc(c.last4)}</b>${c.hint ? ' · scenario idea: ' + esc(c.hint) : ''}` : '';
  }
  if (marketSel) marketSel.onchange = fillCustomers;
  $('#c-cust', el).onchange = showCred;
  fillCustomers();

  const setMode = (m, label) => {
    S.mode = m; const st = $('#c-status', el);
    st.className = 'row small ' + ({ recording: 'st-rec', thinking: 'st-think', speaking: 'st-speak' }[m] || '');
    st.lastElementChild.textContent = label || m;
  };
  const log = $('#c-log', el);
  function add(role, text, meta = '') {
    if ($('.empty', log)) log.innerHTML = '';
    log.insertAdjacentHTML('beforeend', `<div class="bubble ${role}">${esc(text)}${meta ? `<div class="meta">${meta}</div>` : ''}</div>`);
    log.scrollTop = 1e9;
  }
  function render(p) {
    if (p._voice && p.user_text) add('customer', p.user_text, p.latency_ms.asr != null ? `heard by Whisper · ${p.latency_ms.asr} ms` : '');
    let meta = (p.tools || []).map(t => `<span class="chip">${esc(t.tool)}</span>`).join('');
    meta += (p.citations || []).map(c => `<div>📎 ${esc(c)}</div>`).join('');
    if (p.guard) meta += `<div style="color:var(--warn)">guard: ${esc(p.guard.reason)} → ${esc(p.guard.action)}</div>`;
    add('agent', p.reply, meta);
    const s = p.state;
    $('#c-state', el).innerHTML = `<dt>call</dt><dd class="mono">${esc(p.call_id)}</dd><dt>verified</dt><dd>${s.verified ? '<span class="pill good">yes</span>' : '<span class="pill">no</span>'}</dd>
      <dt>disposition</dt><dd>${s.disposition ? `<span class="pill accent">${esc(s.disposition)}</span>` : '—'}</dd>
      <dt>promise</dt><dd>${s.ptp ? esc(`${s.ptp.date} · ${s.ptp.mode} · ${s.ptp.class}`) : '—'}</dd><dt>tickets</dt><dd>${esc((s.tickets || []).join(', ') || '—')}</dd>`;
    const l = p.latency_ms;
    $('#c-lat', el).insertAdjacentHTML('beforeend', `<tr><td>${S.turn++}</td><td class="num">${l.asr ?? '—'}</td><td class="num">${l.agent ?? '—'}</td><td class="num">${l.tts ?? '—'}</td></tr>`);
    S.ended = p.ended;
    if (S.ended) { $('#c-text', el).disabled = true; $('#c-send', el).disabled = true; }
    play(p.audio_b64);
  }
  function play(b64) {
    if (!b64) return afterSpeak();
    setMode('speaking', 'agent speaking');
    S.player.src = 'data:audio/mpeg;base64,' + b64; S.player.onended = afterSpeak; S.player.play().catch(afterSpeak);
  }
  function afterSpeak() {
    if (S.ended) return endCall();
    if ($('#c-mic', el).checked && S.stream) listen(); else setMode('idle', 'your turn – type below');
  }
  async function setupMic() {
    S.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    S.ctx = new AudioContext(); const src = S.ctx.createMediaStreamSource(S.stream);
    S.analyser = S.ctx.createAnalyser(); S.analyser.fftSize = 1024; src.connect(S.analyser);
    S.timer = setInterval(vadTick, 50);
  }
  function listen() {
    if (!S.callId) return;
    S.chunks = []; S.speechMs = 0; S.silenceMs = 0; S.recStart = performance.now();
    S.rec = new MediaRecorder(S.stream, { mimeType: 'audio/webm' });
    S.rec.ondataavailable = e => S.chunks.push(e.data);
    S.rec.onstop = onStop; S.rec.start(); setMode('listening', 'listening… speak now');
  }
  function stopRec(discard) { if (S.rec && S.rec.state !== 'inactive') { S.rec._discard = discard; S.rec.stop(); } }
  function vadTick() {
    if (!S.analyser) return;
    const b = new Float32Array(S.analyser.fftSize); S.analyser.getFloatTimeDomainData(b);
    let s = 0; for (const x of b) s += x * x; const rms = Math.sqrt(s / b.length);
    const meter = $('#c-meter', el); if (meter) meter.style.width = Math.min(100, rms * 800) + '%';
    if (!(S.mode === 'listening' || S.mode === 'recording')) return;
    if (rms > VAD.thr) { S.speechMs += 50; S.silenceMs = 0; if (S.speechMs >= VAD.minSpeech && S.mode === 'listening') setMode('recording', 'hearing you…'); }
    else if (S.mode === 'recording') S.silenceMs += 50;
    const dur = performance.now() - S.recStart;
    if (S.mode === 'recording' && (S.silenceMs >= VAD.endSilence || dur > VAD.maxUtt)) stopRec(false);
    else if (S.mode === 'listening' && dur > 25000) { stopRec(true); setTimeout(listen, 50); }
  }
  async function onStop() {
    if (this._discard || !S.callId) return;
    setMode('thinking', 'transcribing + thinking');
    const fd = new FormData(); fd.append('file', new Blob(S.chunks, { type: 'audio/webm' }), 'speech.webm');
    try { const p = await api(`/api/calls/${S.callId}/turn`, { method: 'POST', body: fd }); p._voice = true; render(p); }
    catch (e) { add('system', 'Turn failed: ' + e.message.slice(0, 120)); afterSpeak(); }
  }
  async function sendText() {
    const inp = $('#c-text', el); const t = inp.value.trim(); if (!t || !S.callId) return;
    inp.value = ''; add('customer', t); stopRec(true); setMode('thinking', 'agent thinking');
    try { render(await api(`/api/calls/${S.callId}/text`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: t }) })); }
    catch (e) { add('system', 'Turn failed: ' + e.message.slice(0, 120)); }
  }
  async function endCall() {
    if (!S.callId) return;
    stopRec(true); S.player.pause();
    const id = S.callId; S.callId = null; setMode('idle', 'call ended');
    $('#c-start', el).disabled = false; $('#c-end', el).disabled = true; $('#c-send', el).disabled = true; $('#c-text', el).disabled = true;
    const r = await api(`/api/calls/${id}/end`, { method: "POST" }).catch(e => ({ crm_summary: { disposition: "error", summary: e.message } }));
    r.crm_summary = r.crm_summary || { disposition: "INCOMPLETE", summary: "" };
    const f = r.files || {};
    $('#c-result', el).innerHTML = `<div class="row"><span class="pill accent">${esc(r.crm_summary.disposition)}</span></div>
      <p>${esc(r.crm_summary.summary || '')}</p>${f.recording ? `<audio controls src="/recordings/${id}/recording.mp3"></audio>` : ''}
      <div class="row mt"><a href="/recordings/${id}/transcript.md" target="_blank">transcript.md</a><a href="/recordings/${id}/call.json" target="_blank">call.json</a></div>`;
  }
  $('#c-start', el).onclick = async () => {
    log.innerHTML = ''; $('#c-lat', el).innerHTML = ''; S.turn = 0; S.ended = false;
    if ($('#c-mic', el).checked && !S.stream) { try { await setupMic(); } catch (e) { $('#c-mic', el).checked = false; add('system', 'Microphone unavailable – type your replies instead.'); } }
    setMode('thinking', 'dialling…');
    try {
      const p = await api('/api/calls', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ market: curMarket(), customer_id: $('#c-cust', el).value }) });
      S.callId = p.call_id; $('#c-callid', el).textContent = p.call_id;
      if (p.outside_calling_hours) add('system', 'Note: outside permitted calling hours for this market – allowed only because this is a test call.');
      $('#c-end', el).disabled = false; $('#c-text', el).disabled = false; $('#c-send', el).disabled = false; $('#c-start', el).disabled = true;
      render(p);
    } catch (e) { setMode('idle', 'failed to start'); add('system', e.message.slice(0, 200)); }
  };
  $('#c-end', el).onclick = endCall;
  $('#c-send', el).onclick = sendText;
  $('#c-text', el).onkeydown = e => { if (e.key === 'Enter') sendText(); };
  onLeave(() => { if (S.callId) endCall(); S.player.pause(); clearInterval(S.timer); S.stream?.getTracks().forEach(t => t.stop()); S.ctx?.close(); });
}

function archDiagram() {
  const lane = (name, sub, steps) => `<div class="lane"><div class="lname">${name}<span>${sub}</span></div><div class="steps">${steps.map((x, i) =>
    `${i ? '<span class="arrow">→</span>' : ''}<div class="step${x[2] ? ' key' : ''}"><b>${x[0]}</b><small>${x[1]}</small></div>`).join('')}</div></div>`;
  return `<div class="pipe">
  ${lane('Q2 · KB build', 'offline, versioned', [['Raw sources', 'HTML · PDF · CSV · forms · notes'], ['Extract & clean', 'boilerplate, OCR/JS flags'], ['Normalise + PII', 'dates, ₹, terms · redaction'], ['Chunk & classify', 'Q&A / row / section units'], ['Dedupe & reconcile', 'supersede · authority wins'], ['Records + index', 'BM25 + Gemini embeddings', 1]])}
  ${lane('Retrieval', 'runtime', [['Hybrid search', 'filters → BM25 + dense → RRF', 1], ['Abstain gate', 'no confident match → nothing'], ['Grounded answer', 'citations · NOT_IN_KB fallback']])}
  <div class="links">↓ the voice engine calls retrieval as a tool (<code>search_knowledge_base</code>) – FAQs are never hard-coded in the prompt</div>
  ${lane('Q1 + Q3 · Voice agent', 'EN · Taglish · Bahasa', [['Mic / Vapi', 'browser or phone'], ['Whisper ASR', 'market language + vocab'], ['Agent LLM', 'tool loop · fallback chain', 1], ['Tools = rules', 'verify · PTP · callback · escalate'], ['Guards', 'numbers · privacy · language · claims', 1], ['Neural TTS', 'en-IN · fil-PH · id-ID'], ['Recording', 'mp3 + stereo wav']])}
  <div class="links">↓ stereo recordings (agent left / customer right) can be replayed into Q4</div>
  ${lane('Q4 · Live nudges', 'real-time', [['Audio stream', '100 ms chunks, 1.0×'], ['VAD endpointing', 'per channel = speaker'], ['Streaming ASR', 'rate-limited Whisper'], ['Rules + LLM', 'µs fast path · JSON signals', 1], ['Nudge engine', 'threshold · merge · cooldown · TTL', 1], ['Dashboard', 'WebSocket, < 2 s']])}
  </div>`;
}

/* ================= views ================= */
const views = {};

views[''] = async v => {
  v.innerHTML = pageHead('AI ENGINEER ASSESSMENT', 'Four working systems, one engine', 'Knowledge-grounded voice agents for loan reminders, a production knowledge base built from messy sources, native-language bots for the Philippines and Indonesia, and real-time call nudges – all measured. Every company, customer and policy here is fictional.') + '<div class="loading">Loading results…</div>';
  const o = await api('/api/overview');
  const ev = o.kb_eval, a = o.asr;
  const card = (href, q, title, desc, kpis) => `<a class="card qcard" href="${href}"><div class="row"><span class="pill accent">${q}</span><h2>${title}</h2></div><div class="muted">${desc}</div>
    <div class="kpis">${kpis.map(([v, l]) => `<div><b>${v}</b><span>${l}</span></div>`).join('')}</div></a>`;
  v.innerHTML = pageHead('AI ENGINEER ASSESSMENT', 'Four working systems, one engine', 'Knowledge-grounded voice agents for loan reminders, a production knowledge base built from messy sources, native-language bots for the Philippines and Indonesia, and real-time call nudges – all measured. Every company, customer and policy here is fictional.') + `
  <div class="grid g2">
    ${card('#/q1', 'Q1', 'Voice agent', 'EMI pre-due reminder: verification, promise-to-pay rules, KB-grounded objections, safe fallback, human escalation. Talk to it in the browser.',
      [[`${o.sims_q1.passed}/${o.sims_q1.total}`, 'test calls pass'], ['ASR in loop', 'TTS → Whisper'], ['8', 'defects fixed in code']])}
    ${card('#/q2', 'Q2', 'Knowledge base', 'HTML, PDF, CSV, forms and PII-laden notes → cleaned, deduplicated, versioned, cited records with hybrid retrieval.',
      [[o.kb.records ?? '—', 'records'], [`${ev.correct}/${ev.correct + ev['partially correct'] + ev.incorrect}`, 'queries correct'], [o.kb.superseded ?? '—', 'superseded versions']])}
    ${card('#/q3', 'Q3', 'Multilingual bots', 'Taglish life-insurance reminders and Bahasa Indonesia multifinance reminders – localized, not translated – with an ASR benchmark.',
      [[`${o.sims_ph.passed}/${o.sims_ph.total}`, 'PH calls pass'], [`${o.sims_id.passed}/${o.sims_id.total}`, 'ID calls pass'], [a.ph_life ? a.ph_life.wer_norm + '%' : '—', 'best PH WER']])}
    ${card('#/q4', 'Q4', 'Live nudges', 'Call audio streamed at real-time speed → streaming ASR → rule + LLM signals → controlled nudges on a live dashboard.',
      [[o.q4.precision + '%', 'precision'], [o.q4.recall + '%', 'recall'], [(o.q4.e2e_p50 / 1000).toFixed(2) + ' s', 'P50 speech → nudge']])}
  </div>
  <div class="grid g2 mt">
    <div class="card"><h3>How to try it</h3><ol class="md" style="margin:0;padding-left:18px">
      <li><a href="#/q1">Q1 → Live call</a>: start a call, allow the mic, and play the customer. The test identity is shown above the call.</li>
      <li><a href="#/q2">Q2 → Ask</a>: ask a policy question; try an out-of-scope one to see the safe refusal.</li>
      <li><a href="#/q3">Q3 → Live call</a>: switch to the Philippines or Indonesia bot and speak Taglish or Bahasa.</li>
      <li><a href="#/q4">Q4 → Live replay</a>: play a recorded call and watch nudges arrive while it plays.</li>
      <li>Every tab has a <b>Test calls / Results</b> view with recordings, transcripts and pass/fail checks.</li></ol></div>
    <div class="card"><h3>Quick links</h3>
      <div class="md small"><p><b>Q2</b> builds the KB → the <b>Q1/Q3</b> engine retrieves from it through a tool, enforces business rules in code, and checks every number it says against the KB or CRM (grounding guard) → calls are recorded in stereo → <b>Q4</b> can replay any of them live.</p>
      <p>LLM: Groq (Qwen3.8-27B / gpt-oss) with automatic fallback to Gemini and OpenRouter · ASR: Groq Whisper · TTS: neural voices (en-IN, fil-PH, id-ID) · Embeddings: Gemini.</p>
      <p><a href="#/docs">Architecture, limitations and production plan →</a></p></div></div>
  </div>
  <div class="card mt"><h3 style="margin-bottom:12px">How it fits together</h3>${archDiagram()}</div>`;
};

views.q1 = async (v, sub = 'live') => {
  v.innerHTML = pageHead('Q1 · KNOWLEDGE-GROUNDED VOICE AGENT', 'Loan pre-due reminder agent', 'Udaan Credit Finance (fictional NBFC). The agent verifies identity, reminds the EMI, classifies the promise to pay against the grace period, answers objections only from the knowledge base, and escalates to a human when needed.') + '<div class="tabs" id="t"></div><div id="tv"></div>';
  const pick = k => { location.hash = '#/q1/' + k; };
  tabs($('#t'), [['live', 'Live call'], ['tests', 'Test calls'], ['design', 'Script & rules'], ['findings', 'Defects found & fixed']], sub, pick);
  const tv = $('#tv');
  if (sub === 'live') await callPanel(tv, ['in_lender']);
  else if (sub === 'tests') await simTable(tv, 'q1', 'Automated test calls');
  else if (sub === 'design') { tv.innerHTML = '<div class="grid g2"><div class="card" id="d1"></div><div class="card" id="d2"></div></div>'; mdInto($('#d1'), 'q1-script'); mdInto($('#d2'), 'q1-rules'); }
  else { tv.innerHTML = '<div class="card" id="d1"></div>'; mdInto($('#d1'), 'q1-results'); }
};

views.q2 = async (v, sub = 'ask') => {
  v.innerHTML = pageHead('Q2 · PRODUCTION-READY KNOWLEDGE BASE', 'Knowledge base', 'Mixed sources → extraction → boilerplate removal → normalisation → PII redaction → classification → chunking → dedupe and versioning → conflict reconciliation → BM25 + Gemini embeddings.') + '<div class="tabs" id="t"></div><div id="tv"></div>';
  tabs($('#t'), [['ask', 'Ask the KB'], ['records', 'Records'], ['eval', 'Retrieval evaluation'], ['build', 'Build report']], sub, k => location.hash = '#/q2/' + k);
  const tv = $('#tv');
  if (sub === 'ask') {
    const ex = { in_lender: ['Will a late payment affect my CIBIL score?', 'How much is the bounce charge if auto-debit fails?', 'My salary is late, I don\'t have money right now', 'What is your gold loan interest rate?'],
      ph_life: ['Ano po mangyayari kapag na-lapse yung policy ko?', 'Sabi ng bangko parang savings lang daw ito', 'Paano magbayad ng premium?'],
      id_multifinance: ['Berapa dendanya kalau saya telat bayar cicilan?', 'Bayar angsuran bisa lewat Indomaret nggak?', 'Kalau pelunasan dipercepat ada penalti?'] };
    tv.innerHTML = `<div class="card"><div class="row"><select id="k-m">${Object.keys(MARKET_LABEL).map(m => `<option value="${m}">${MARKET_LABEL[m]}</option>`).join('')}</select>
      <input type="search" id="k-q" placeholder="Ask a customer question…"><button class="btn primary" id="k-go">Ask</button></div><div class="row mt" id="k-ex"></div></div><div id="k-out" class="mt"></div>`;
    const fillEx = () => { $('#k-ex').innerHTML = '<span class="small muted">Try:</span>' + ex[$('#k-m').value].map(q => `<button class="btn small" data-q="${esc(q)}">${esc(q)}</button>`).join(''); $$('#k-ex button').forEach(b => b.onclick = () => { $('#k-q').value = b.dataset.q; ask(); }); };
    $('#k-m').onchange = fillEx; fillEx();
    async function ask() {
      const q = $('#k-q').value.trim(); if (!q) return; const m = $('#k-m').value; const out = $('#k-out');
      out.innerHTML = '<div class="loading">Searching and generating a grounded answer…</div>';
      const enc = encodeURIComponent(q);
      const [s, a] = await Promise.all([api(`/api/kb/search?q=${enc}&market=${m}`), api(`/api/kb/answer?q=${enc}&market=${m}`).catch(e => ({ status: 'error', reason: e.message }))]);
      const ans = a.status === 'answered' ? `<div class="answer">${esc(a.answer)}<div class="small muted mt">${(a.citations || []).map(esc).join('<br>')}</div></div>`
        : `<div class="answer none"><b>Not in the knowledge base → safe fallback.</b><br>“I don't have that information right now; I can arrange a callback.”<div class="small muted">${esc(a.reason || '')}</div></div>`;
      out.innerHTML = `<div class="grid g2"><div><h3 style="margin-bottom:8px">Grounded answer</h3>${ans}
        <p class="small muted">Retrieval: ${esc(s.meta.mode)} · ${s.meta.latency_ms} ms · ${s.meta.abstained ? 'abstained (no confident match)' : 'confident'}${a.llm_ms ? ` · LLM ${a.llm_ms} ms` : ''}</p></div>
        <div><h3 style="margin-bottom:8px">Retrieved records</h3>${s.hits.length ? s.hits.map(h => `<div class="hit"><div class="row"><b>${esc(h.title)}</b><span class="pill">${esc(h.category)}</span></div>
          <p style="margin:6px 0">${esc(h.content)}</p><div class="mono muted">${esc(h.citation)}</div><div class="small muted">BM25 ${h.bm25} · dense ${h.dense ?? '—'} · coverage ${h.coverage}</div></div>`).join('') : '<div class="empty">No record passed the confidence gate.</div>'}</div></div>`;
    }
    $('#k-go').onclick = ask; $('#k-q').onkeydown = e => { if (e.key === 'Enter') ask(); };
  } else if (sub === 'records') {
    tv.innerHTML = `<div class="card"><div class="row"><select id="r-m"><option value="">All markets</option></select><select id="r-c"><option value="">All categories</option></select>
      <select id="r-s"><option value="">Any status</option><option value="active">active</option><option value="superseded">superseded</option></select><input type="search" id="r-q" placeholder="Filter text or record id"><span id="r-n" class="small muted"></span></div></div><div class="card mt table-wrap" id="r-t"></div>`;
    let first = true;
    async function load() {
      const p = new URLSearchParams({ market: $('#r-m').value, category: $('#r-c').value, status: $('#r-s').value, q: $('#r-q').value });
      const d = await api('/api/kb/records?' + p);
      if (first) { first = false; $('#r-m').innerHTML += d.facets.market.map(m => `<option>${m}</option>`).join(''); $('#r-c').innerHTML += d.facets.category.map(m => `<option>${m}</option>`).join(''); }
      $('#r-n').textContent = `${d.total} records`;
      $('#r-t').innerHTML = `<table><thead><tr><th>Record</th><th>Title</th><th>Category</th><th>Market</th><th>Status</th><th>Flags</th></tr></thead><tbody>${d.records.map((r, i) => `<tr class="click" data-i="${i}">
        <td class="mono">${esc(r.record_id)}</td><td>${esc(r.title)}</td><td><span class="pill">${esc(r.category)}</span></td><td class="small">${esc(r.market)}</td>
        <td>${r.status === 'active' ? '<span class="pill good">active</span>' : '<span class="pill warn">superseded</span>'}</td>
        <td>${r.pii ? '<span class="pill bad">PII redacted</span> ' : ''}${(r.corrections || []).length ? '<span class="pill warn">corrected</span>' : ''}${r.audience === 'internal' ? ' <span class="pill">internal</span>' : ''}</td></tr>`).join('')}</tbody></table>`;
      $$('#r-t tr.click').forEach(tr => tr.onclick = () => {
        const r = d.records[+tr.dataset.i];
        openDrawer(r.record_id, `<h2>${esc(r.title)}</h2><p>${esc(r.content)}</p>
          <dl class="kv mt"><dt>source</dt><dd class="mono">${esc(r.source.uri)} § ${esc(r.source.section)}${r.source.page ? ' p.' + r.source.page : ''}</dd><dt>version</dt><dd>${esc(r.version)} · ${esc(r.effective_date || '')}</dd>
          <dt>status</dt><dd>${esc(r.status)}${r.superseded_by ? ' → ' + esc(r.superseded_by) : ''}</dd><dt>topics</dt><dd>${esc(r.topics.join(', '))}</dd><dt>audience</dt><dd>${esc(r.audience)}</dd>
          <dt>PII</dt><dd>${r.pii ? 'redacted: ' + esc(r.pii_redacted.join(', ')) : 'none'}</dd></dl>
          ${(r.corrections || []).map(c => `<div class="answer none mt"><b>Source error corrected</b><br>“${esc(c.original)}” → “${esc(c.corrected)}”<div class="small muted">authority: ${esc(c.authoritative_source)}</div></div>`).join('')}
          <h3 class="mt">Raw record</h3><pre class="md"><code>${esc(JSON.stringify(r, null, 2))}</code></pre>`);
      });
    }
    ['#r-m', '#r-c', '#r-s'].forEach(s => $(s).onchange = load); let t; $('#r-q').oninput = () => { clearTimeout(t); t = setTimeout(load, 250); };
    load();
  } else if (sub === 'eval') {
    const rows = await api('/api/kb/eval');
    const c = v => rows.filter(r => r.verdict === v).length;
    tv.innerHTML = `<div class="grid g4"><div class="card stat"><span class="v">${rows.length}</span><span class="l">test queries</span></div><div class="card stat"><span class="v">${c('correct')}</span><span class="l">correct (top-1)</span></div>
      <div class="card stat"><span class="v">${c('partially correct')}</span><span class="l">partially correct (top-3)</span></div><div class="card stat"><span class="v">${c('incorrect')}</span><span class="l">incorrect</span></div></div>
      <div class="card mt table-wrap"><table><thead><tr><th>#</th><th>Type</th><th>Question</th><th>Top record</th><th>Verdict</th></tr></thead><tbody>${rows.map((r, i) => `<tr class="click" data-i="${i}">
      <td class="mono">${r.id}</td><td><span class="pill">${esc(r.type)}</span></td><td>${esc(r.question)}</td><td class="small">${r.top ? esc(r.top.title) : '<i>abstained</i>'}</td>
      <td><span class="pill ${r.verdict === 'correct' ? 'good' : r.verdict === 'incorrect' ? 'bad' : 'warn'}">${esc(r.verdict)}</span></td></tr>`).join('')}</tbody></table></div>`;
    $$('tr.click', tv).forEach(tr => tr.onclick = () => {
      const r = rows[+tr.dataset.i]; const a = r.answer;
      openDrawer(r.id + ' · ' + r.type, `<h2>${esc(r.question)}</h2><p class="muted">${esc(r.relevance)}</p>
        ${a ? (a.status === 'answered' ? `<div class="answer">${esc(a.answer)}</div>` : `<div class="answer none">NOT_IN_KB → safe fallback (${esc(a.reason)})</div>`) : ''}
        ${r.top ? `<h3 class="mt">Top record</h3><div class="hit"><b>${esc(r.top.title)}</b><p>${esc(r.top.content)}</p><div class="mono muted">${esc(r.top.citation)}</div></div>` : '<div class="empty">Retrieval abstained</div>'}`);
    });
  } else { tv.innerHTML = '<div class="card" id="d1"></div>'; mdInto($('#d1'), 'kb-build'); }
};

views.q3 = async (v, sub = 'live') => {
  v.innerHTML = pageHead('Q3 · NATIVE-LANGUAGE VOICE BOTS', 'Philippines & Indonesia', 'Same engine, re-authored per market: Taglish life-insurance premium reminders (Bituin Life) and Bahasa Indonesia multifinance instalment reminders (Pundi Mitra), with market-specific ASR, native neural voices, localized fallbacks and regional-language handling.') + '<div class="tabs" id="t"></div><div id="tv"></div>';
  tabs($('#t'), [['live', 'Live call'], ['tests', 'Test calls'], ['asr', 'ASR benchmark'], ['local', 'Localization'], ['findings', 'Findings']], sub, k => location.hash = '#/q3/' + k);
  const tv = $('#tv');
  if (sub === 'live') await callPanel(tv, ['ph_life', 'id_multifinance']);
  else if (sub === 'tests') { tv.innerHTML = '<div class="card" id="s1"></div><div class="card mt" id="s2"></div>'; await Promise.all([simTable($('#s1'), 'ph', 'Philippines (Taglish)'), simTable($('#s2'), 'id', 'Indonesia (Bahasa, incl. Javanese & Sundanese accents)')]); }
  else if (sub === 'asr') {
    const d = await api('/api/asr');
    const ph = d.ph_life, id = d.id_multifinance;
    const cfgs = [...new Set([...(ph?.configs || []), ...(id?.configs || [])].map(c => c.config))];
    const rows = cfgs.map(c => ({ label: c, ph: ph?.configs.find(x => x.config === c)?.wer_norm, id: id?.configs.find(x => x.config === c)?.wer_norm }));
    tv.innerHTML = `<div class="grid g4">
      <div class="card stat"><span class="v">${ph ? Math.min(...ph.configs.map(c => c.wer_norm)) : '—'}%</span><span class="l">best PH word error rate</span></div>
      <div class="card stat"><span class="v">${id ? Math.min(...id.configs.map(c => c.wer_norm)) : '—'}%</span><span class="l">best ID word error rate</span></div>
      <div class="card stat"><span class="v">${[...(ph?.configs || []), ...(id?.configs || [])].reduce((a, c) => a + c.translated, 0)}</span><span class="l">translated-to-English failures</span></div>
      <div class="card stat"><span class="v">${[...(ph?.configs || []), ...(id?.configs || [])].reduce((a, c) => a + c.n, 0)}</span><span class="l">transcriptions</span></div></div>
      <div class="card mt"><h3>Word error rate by ASR configuration (numbers normalised, lower is better)</h3><div id="ch1"></div></div>
      <div class="grid g2 mt"><div class="card"><h3>Indonesia · by speaker voice (regional accent)</h3><div id="ch2"></div><p class="small muted">jv-ID = Javanese-accented, su-ID = Sundanese-accented neural voices reading Indonesian. Reference config: ${esc(id?.reference_config || '')}.</p></div>
      <div class="card"><h3>Philippines · by speaker voice</h3><div id="ch3"></div><p class="small muted">en-PH = Filipino-English voice reading Taglish. Reference config: ${esc(ph?.reference_config || '')}.</p></div></div>
      <div class="card mt table-wrap"><h3>Configurations (table view)</h3><table><thead><tr><th>Market</th><th>Config</th><th class="num">n</th><th class="num">WER</th><th class="num">WER (num-norm)</th><th class="num">Term recall</th><th class="num">p50 latency</th></tr></thead><tbody>
      ${Object.entries(d).flatMap(([m, x]) => x.configs.map(c => `<tr><td>${m === 'ph_life' ? 'PH' : 'ID'}</td><td>${esc(c.config)}${c.config === x.best_config ? ' <span class="pill good">best</span>' : ''}</td><td class="num">${c.n}</td><td class="num">${c.wer}%</td><td class="num"><b>${c.wer_norm}%</b></td><td class="num">${c.term_recall}%</td><td class="num">${c.latency_ms} ms</td></tr>`)).join('')}</tbody></table></div>
      <div class="card mt" id="ex"></div>`;
    barChart($('#ch1'), { rows, series: [{ name: 'Philippines (Taglish)', key: 'ph', color: '--series-1' }, { name: 'Indonesia (Bahasa)', key: 'id', color: '--series-2' }], unit: '%', labelW: 290 });
    if (id) barChart($('#ch2'), { rows: id.voices.map(x => ({ label: x.name, v: x.wer_norm })), series: [{ name: 'WER', key: 'v', color: '--series-1' }], unit: '%', labelW: 170 });
    if (ph) barChart($('#ch3'), { rows: ph.voices.map(x => ({ label: x.name, v: x.wer_norm })), series: [{ name: 'WER', key: 'v', color: '--series-1' }], unit: '%', labelW: 170 });
    const exs = [...(ph?.examples || []).slice(0, 3), ...(id?.examples || []).slice(0, 3)];
    $('#ex').innerHTML = `<h3>Hardest utterances</h3>${exs.map(r => `<div class="hit"><div class="row"><span class="pill">${esc(r.market === 'ph_life' ? 'PH' : 'ID')}</span><span class="mono">${esc(r.voice)}</span><span class="pill warn">WER ${(r.wer_norm * 100).toFixed(0)}%</span></div>
      <div class="small mt"><b>said:</b> ${esc(r.ref)}<br><b>heard:</b> ${esc(r.hyp)}</div></div>`).join('')}`;
  } else if (sub === 'local') { tv.innerHTML = '<div class="card" id="d1"></div>'; mdInto($('#d1'), 'q3-readme'); }
  else { tv.innerHTML = '<div class="card" id="d1"></div>'; mdInto($('#d1'), 'q3-findings'); }
};

views.q4 = async (v, sub = 'live') => {
  v.innerHTML = pageHead('Q4 · LIVE INSIGHTS & NUDGES', 'Real-time call nudges', 'Call audio is streamed at real-time speed in 100 ms chunks. Per-channel VAD → streaming Whisper → rule + LLM signal extraction → a nudge engine with thresholds, grouping, cooldowns and expiry → this dashboard over a WebSocket.') + '<div class="tabs" id="t"></div><div id="tv"></div>';
  tabs($('#t'), [['live', 'Live replay'], ['results', 'Results'], ['reports', 'Reports']], sub, k => location.hash = '#/q4/' + k);
  const tv = $('#tv');
  if (sub === 'live') {
    const sc = await api('/api/scenarios');
    tv.innerHTML = `<div class="card"><div class="row"><select id="n-sc">${sc.map(s => `<option value="${s.id}">${esc(s.title)}</option>`).join('')}</select>
      <select id="n-asr"><option value="groq">ASR: Groq Whisper (real)</option><option value="mock">ASR: mock (offline)</option></select>
      <label class="row small" style="gap:6px"><input type="checkbox" id="n-llm" checked> LLM signals</label><label class="row small" style="gap:6px"><input type="checkbox" id="n-play" checked> play audio</label>
      <span class="spacer"></span><button class="btn primary" id="n-go">Start live replay</button></div><div id="n-desc" class="small muted" style="margin-top:8px"></div></div>
      <div class="call mt"><div class="card"><div class="row"><h3>Live transcript</h3><span class="spacer"></span><span id="n-status" class="small muted">idle</span></div><div class="log" id="n-tx"><div class="empty">Choose a scenario and start. Agent and customer are separated by stereo channel.</div></div></div>
      <div class="grid" style="align-content:start"><div class="card"><h3>Nudges for the agent</h3><div id="n-list" class="grid" style="gap:8px"><div class="small muted">Nudges appear within seconds of the trigger.</div></div></div>
      <div class="card"><h3>Latency</h3><div class="grid g3" style="gap:8px"><div class="stat"><span class="v" id="n-e2e">–</span><span class="l small">last nudge (ms)</span></div><div class="stat"><span class="v" id="n-asrl">–</span><span class="l small">last ASR (ms)</span></div><div class="stat"><span class="v" id="n-cnt">0</span><span class="l small">nudges</span></div></div>
      <div id="n-topics" class="row mt" style="gap:4px"></div></div><div class="card"><h3>Events</h3><div id="n-log" class="small muted" style="max-height:180px;overflow:auto"></div></div></div></div>`;
    const desc = () => $('#n-desc').textContent = sc.find(s => s.id === $('#n-sc').value)?.description || '';
    $('#n-sc').onchange = desc; desc();
    const player = new Audio(); let ws, count = 0, alive = true;
    const evlog = t => $('#n-log').insertAdjacentHTML('afterbegin', `<div>${esc(t)}</div>`);
    function connect() {
      ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
      ws.onmessage = e => handle(JSON.parse(e.data)); ws.onclose = () => { if (alive) setTimeout(connect, 1000); };
    }
    connect();
    onLeave(() => { alive = false; player.pause(); ws && ws.close(); });
    $('#n-go').onclick = () => {
      $('#n-tx').innerHTML = ''; $('#n-list').innerHTML = ''; $('#n-log').innerHTML = ''; $('#n-topics').innerHTML = ''; count = 0; $('#n-cnt').textContent = 0;
      const id = $('#n-sc').value;
      ws.send(JSON.stringify({ action: 'run', scenario: id, asr: $('#n-asr').value, llm: $('#n-llm').checked, speed: 1 }));
      if ($('#n-play').checked) { player.src = `/audio/${id}.wav`; player.play().catch(() => { }); }
    };
    function handle(m) {
      const d = m.data;
      if (m.type === 'start') $('#n-status').textContent = `streaming ${d.duration}s · ASR ${d.asr} · LLM ${d.llm ? 'on' : 'off'}`;
      else if (m.type === 'transcript') { $('#n-tx').insertAdjacentHTML('beforeend', `<div class="bubble ${d.speaker}">${esc(d.text)}<div class="meta">${d.speaker} · ${d.start_t}s · ASR ${d.asr_ms} ms · audio→text ${d.audio_to_text_ms} ms</div></div>`); $('#n-tx').scrollTop = 1e9; $('#n-asrl').textContent = d.asr_ms; }
      else if (m.type === 'nudge') {
        count++; $('#n-cnt').textContent = count;
        $('#n-list').insertAdjacentHTML('afterbegin', `<div class="nudge p${d.priority}" id="nd-${d.id}"><b>P${d.priority} · ${esc(d.label)}</b>${esc(d.text)}<div class="small muted mt">${esc(d.type)} · ${esc(d.source)} ${d.confidence} · <span class="lat">…</span></div></div>`);
      }
      else if (m.type === 'nudge_latency') { const e = $(`#nd-${d.id} .lat`); if (e) e.textContent = `${d.latency_ms.e2e} ms from end of speech`; $('#n-e2e').textContent = Math.round(d.latency_ms.e2e); }
      else if (m.type === 'nudge_update') { evlog(`${d.id} duplicate merged (${d.type}) ×${d.updates}`); }
      else if (m.type === 'nudge_close') { const e = $(`#nd-${d.id}`); if (e) { e.classList.add('closed'); $('b', e).insertAdjacentText('beforeend', ` – ${d.status}`); } evlog(`${d.id} ${d.status}`); }
      else if (m.type === 'topic_shift') $('#n-topics').insertAdjacentHTML('beforeend', `<span class="pill">${esc(d.to)}</span>`);
      else if (m.type === 'sentiment') evlog(`customer frustration ${d.frustration}`);
      else if (m.type === 'asr_error') evlog('ASR segment dropped: ' + d.error);
      else if (m.type === 'summary') { const pc = d.post_call; evlog(`CALL END · ${pc.total_nudges} nudges · acted on ${pc.acted_on} · missed opportunities ${pc.missed_opportunities.length} · unresolved compliance ${pc.unresolved_compliance.length}`); $('#n-status').textContent += ' · finished'; }
    }
  } else if (sub === 'results') {
    tv.innerHTML = `<div class="row" style="margin-bottom:12px"><select id="q-mode"><option value="llm">Rules + LLM signals</option><option value="rules">Rules only (ablation)</option></select><span class="small muted">Real Groq Whisper, real-time replay, labelled scenarios.</span></div><div id="q-body"><div class="loading">Loading…</div></div>`;
    async function load() {
      const d = await api('/api/q4/results?mode=' + $('#q-mode').value);
      const comp = ['endpointing', 'asr', 'signal', 'engine', 'delivery'].filter(k => d.components[k]).map(k => ({ label: k, p50: d.components[k].p50, p95: d.components[k].p95 }));
      $('#q-body').innerHTML = `<div class="grid g4"><div class="card stat"><span class="v">${d.precision}%</span><span class="l">precision (${d.tp} TP · ${d.fp} FP)</span></div>
        <div class="card stat"><span class="v">${d.recall}%</span><span class="l">recall (${d.fn} missed)</span></div>
        <div class="card stat"><span class="v">${d.e2e_p50 ? (d.e2e_p50 / 1000).toFixed(2) + ' s' : '—'}</span><span class="l">P50 end of speech → nudge shown</span></div>
        <div class="card stat"><span class="v">${d.e2e_p95 ? (d.e2e_p95 / 1000).toFixed(2) + ' s' : '—'}</span><span class="l">P95 end of speech → nudge shown</span></div></div>
        <div class="card mt"><h3>Latency per pipeline stage (ms, per nudge)</h3><div id="q-ch"></div></div>
        ${d.runs.map(r => `<div class="card mt"><div class="row"><h3>${esc(r.title)}</h3><span class="spacer"></span>${r.missed.length ? `<span class="pill bad">missed: ${esc(r.missed.join(', '))}</span>` : ''}<span class="pill">${r.nudges.length} nudges</span><span class="pill">${r.stats.duplicates_merged} merged</span></div>
          <p class="small muted">${esc(r.description)}</p>${r.nudges.length ? `<div class="table-wrap"><table><thead><tr><th>Nudge</th><th>Evidence</th><th>Path</th><th>Verdict</th><th class="num">e2e ms</th></tr></thead><tbody>
          ${r.nudges.map(n => `<tr><td><b>P${n.priority} ${esc(n.label)}</b><div class="small muted">${esc(n.type)}</div></td><td class="small">“${esc((n.evidence || [''])[0])}”</td><td><span class="pill">${esc(n.path || n.source)}</span></td>
            <td><span class="pill ${n.verdict === 'TP' ? 'good' : n.verdict === 'FP' ? 'bad' : ''}">${n.verdict}</span></td><td class="num">${Math.round(n.latency_ms.e2e)}</td></tr>`).join('')}</tbody></table></div>` : '<div class="empty" style="padding:10px">No nudges – correct for this call.</div>'}</div>`).join('')}`;
      barChart($('#q-ch'), { rows: comp, series: [{ name: 'P50', key: 'p50', color: '--series-1' }, { name: 'P95', key: 'p95', color: '--series-2' }], unit: '', labelW: 120, decimals: 0 });
    }
    $('#q-mode').onchange = load; load();
  } else {
    tv.innerHTML = `<div class="tabs" id="t2" style="margin-top:-6px"></div><div class="card" id="d1"></div>`;
    const sw = k => { tabs($('#t2'), [['q4-readme', 'Overview'], ['q4-latency', 'Latency report'], ['q4-fp', 'False-positive analysis'], ['q4-latency-rules', 'Rules-only latency'], ['q4-fp-rules', 'Rules-only FP']], k, sw); mdInto($('#d1'), k); };
    sw('q4-readme');
  }
};

views.docs = async (v, sub = 'readme') => {
  v.innerHTML = pageHead('PROJECT', 'Docs & architecture', '') + '<div class="tabs" id="t"></div><div class="card" id="d1"></div>';
  tabs($('#t'), [['readme', 'README'], ['architecture', 'Architecture'], ['limitations', 'Limitations & production plan'], ['video', 'Video walkthrough script']], sub, k => location.hash = '#/docs/' + k);
  if (sub === 'architecture') {
    const t = await api('/api/doc/architecture');
    $('#d1').innerHTML = `<h2 style="margin-bottom:12px">Architecture</h2>${archDiagram()}<div class="md mt">${md(t.replace(/^# .*\n/, '').replace(/```mermaid[\s\S]*?```/, ''))}</div>`;
  } else mdInto($('#d1'), sub);
};

/* ---------------- router ---------------- */
async function route() {
  leave(); closeDrawer(); $('#side').classList.remove('open');
  const [, page = '', sub] = (location.hash || '#/').split('/');
  $$('#nav a').forEach(a => a.classList.toggle('active', a.dataset.r === page));
  const v = $('#view'); v.innerHTML = '<div class="loading">Loading…</div>'; window.scrollTo(0, 0);
  try { await (views[page] || views[''])(v, sub || undefined); }
  catch (e) { v.innerHTML = `<div class="card empty">Something went wrong: ${esc(e.message.slice(0, 300))}</div>`; }
}
addEventListener('hashchange', route);
loadStatus(); route();
