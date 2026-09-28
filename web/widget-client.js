(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const ui = Object.fromEntries(['start','mic','mic-lang','status','status-dot','screen','screen-empty','screen-status','empty-description','notice','error','messages','message','send','suggestions','voice','voice-status','replay','stop','end','steps','activity','viewer-caption'].map(id=>[id,$(id)]));
  const parentOrigin = new URLSearchParams(location.search).get('parent_origin') || location.origin;
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  // Per-viewer convenience only; storage can be unavailable in private windows.
  const prefs = {get(k){try{return localStorage.getItem(k);}catch{return null;}}, set(k,v){try{localStorage.setItem(k,v);}catch{}}};
  let session = null, state = null, timer = null, starting = false, sending = false, ending = false, closed = false;
  let failures = 0, stopPending = false, pollRunning = false, frameLoopRunning = false, shownFrameURL = null, hasFrame = false;
  let lastStateError = '', stepsKey = '', firstRender = true;
  const rendered = new Map();
  const active = () => !!session && !ending && !closed;
  const ready = () => active() && ['ready','active','login_required'].includes(state?.status) && !state?.busy && !sending && !stopPending;
  // A new question may be sent while Beacon is working; it interrupts the running demonstration.
  const canSend = () => active() && ['ready','active','login_required'].includes(state?.status) && !sending && !stopPending;
  let voiceHold = -1;
  // Latency marks per turn (performance.now() ms): heard = final speech result, sent, reply shown, audio playing.
  const latency = window.__beaconLatency = [];
  let heardAt = null;
  // Stage timings from the server for this session (used by eval/latency.py); the token itself is not exposed.
  window.__beaconTimings = () => session ? request(endpoint('/timings')).then(r=>r.json()) : Promise.resolve(null);
  const mark = (name) => { const turn = latency[latency.length - 1]; if (turn && turn[name] == null) turn[name] = Math.round(performance.now()); };
  function setText(el, text) { if (el.textContent !== text) el.textContent = text; }
  function show(el, text) { setText(el, text || ''); el.hidden = !text; }
  const error = text => show(ui.error, text);
  const notice = text => show(ui.notice, text);
  function controls() {
    $('close').disabled = starting || ending;
    ui.start.hidden = !!session; ui.start.disabled = starting; setText(ui.start, starting ? 'Connecting…' : 'Start a session ↗');
    ui.message.disabled = !canSend(); ui.send.disabled = !canSend() || !ui.message.value.trim(); ui.mic.disabled = !session || ending;
    ui.suggestions.hidden = !session; ui.suggestions.querySelectorAll('button').forEach(b=>b.disabled=!canSend());
    ui.end.disabled = !session || ending; ui.stop.disabled = !session || stopPending || !state?.busy;
    ui.replay.disabled = !active() || !state?.messages?.some(m=>m.role==='assistant');
  }
  async function request(path, options = {}, target = session, timeoutMs = 15000) {
    const controller = new AbortController(); const timeout = setTimeout(()=>controller.abort(), timeoutMs);
    try {
      const response = await fetch(path,{...options,signal:controller.signal,headers:{...(options.body?{'Content-Type':'application/json'}:{}),...(target?{'X-Beacon-Token':target.token}:{}),...options.headers}});
      if (!response.ok) {
        let detail = ''; try { const data = await response.json(); detail = typeof data.detail === 'string' ? data.detail : data.message || ''; } catch {}
        const e = new Error(detail || (response.status===409 ? 'Another session or action is already running. Please wait and try again.' : 'Beacon could not complete that request. Please try again.'));
        e.status = response.status; throw e;
      }
      return response;
    } catch(e) { if(e.name==='AbortError') throw new Error('The connection timed out. Check that Beacon is running and try again.'); throw e; }
    finally { clearTimeout(timeout); }
  }
  function endpoint(suffix='',target=session){return '/api/sessions/'+encodeURIComponent(target.id)+suffix;}

  // ---- Conversation: append new bubbles instead of rebuilding the list (rebuilding reset the scroll and flickered).
  const typing = document.createElement('div'); typing.className = 'typing'; typing.setAttribute('aria-label','Beacon is working');
  typing.append(...[0,1,2].map(()=>document.createElement('i')));
  function renderMessages(messages, busy) {
    const box = ui.messages, ids = new Set(messages.map(m=>m.id));
    const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 120;
    for (const [id, el] of rendered) if (!ids.has(id)) { el.remove(); rendered.delete(id); }
    let added = false, previousRole = null;
    for (const m of messages) {
      const existing = rendered.get(m.id);
      if (existing) { previousRole = m.role; continue; }
      if (!rendered.size) box.replaceChildren();
      const article = document.createElement('article'); article.className = 'message ' + (m.role==='user' ? 'user' : 'assistant');
      // Consecutive Beacon replies read as one turn; only the first carries the name.
      if (m.role === previousRole && m.role === 'assistant') article.classList.add('continued');
      const name = document.createElement('span'); name.className = 'speaker'; name.textContent = m.role==='user' ? 'You' : 'Beacon';
      const text = document.createElement('div'); text.textContent = m.text || '';
      article.append(name, text); box.append(article); rendered.set(m.id, article); added = true; previousRole = m.role;
    }
    if (busy) { if (box.lastElementChild !== typing) { box.append(typing); added = true; } }
    else if (typing.isConnected) typing.remove();
    if (added && (nearBottom || firstRender)) box.scrollTo({top: box.scrollHeight, behavior: firstRender ? 'instant' : 'smooth'});
    if (messages.length) firstRender = false;
  }
  function renderSteps(steps) {
    const key = JSON.stringify(steps); if (key === stepsKey) return; stepsKey = key;
    ui.activity.hidden = !steps.length; ui.steps.replaceChildren();
    steps.forEach(step=>{const li=document.createElement('li');li.className='step-'+(step.status||'');li.textContent=step.title||'Workspace action';const detail=document.createElement('span');detail.textContent=[step.status,step.detail].filter(Boolean).join(' · ');li.append(detail);ui.steps.append(li);});
  }
  function render(next) {
    state = next;
    const label = {ready:'Ready to explore',active:'Ready to explore',login_required:'Waiting for CRM sign-in',starting:'Preparing workspace',initializing:'Preparing workspace',stopped:'Walkthrough stopped',error:'Session needs attention',ended:'Session ended',closed:'Session ended'}[next.status] || 'Preparing workspace';
    setText(ui.status, next.busy ? 'Exploring your workspace…' : label);
    const dot = next.busy ? 'busy' : ['ready','active'].includes(next.status) ? 'ready' : '';
    if (ui['status-dot'].className !== dot) ui['status-dot'].className = dot;
    if (next.status==='login_required') { notice(next.login_help || 'The demo browser is not signed in to the CRM yet. This view updates automatically after sign-in.'); setText(ui['empty-description'], 'Waiting for the demo browser to sign in to the CRM. No sign-in is needed in this window.'); }
    else if (['starting','initializing'].includes(next.status)) { notice(''); setText(ui['empty-description'], 'Preparing your live workspace. This takes a few seconds.'); }
    else { notice(''); if (!hasFrame) setText(ui['empty-description'], 'Your session is connected. The live workspace will appear here.'); }
    if (next.last_error && next.last_error!==lastStateError) {lastStateError=next.last_error; error(typeof next.last_error==='string'?next.last_error:'The walkthrough needs attention. Try another question.');}
    const messages = Array.isArray(next.messages) ? next.messages : [];
    renderMessages(messages, !!next.busy);
    // Speak only the reply to the latest question; replies to an interrupted one are skipped.
    const users = messages.filter(m=>m.role==='user').length;
    if (voiceHold >= 0 && users > voiceHold) voiceHold = -1;
    if (voiceHold < 0) {
      const lastUser = messages.map(m=>m.role).lastIndexOf('user');
      messages.forEach((m,i)=>{ if (m.role==='assistant') { if (i < lastUser) voiceQueue.skip(m); else { voiceQueue.offer(m); mark('shown'); } } });
    }
    renderSteps(Array.isArray(next.steps) ? next.steps : []);
    if (next.status === 'login_required' && hasFrame) clearScreen();
    controls();
    talk.refresh();
  }
  async function poll(target) {
    if(!active() || target!==session || pollRunning) return;
    clearTimeout(timer);pollRunning=true;
    try {
      const response=await request(endpoint('',target),{},target);const next=await response.json();
      if(target!==session || !active())return;
      if(failures) {error('');failures=0;}
      render(next);
      if(['ended','closed'].includes(next.status)){await endSession(false);return;}
      if(!frameLoopRunning) frameLoop(target);
    } catch(e) {
      if(target!==session || !active())return;
      failures++;setText(ui['screen-status'],'Connection interrupted');error(e.message || 'Unable to reach Beacon. Check that the demo service is running.');
      if([401,403,404,410].includes(e.status)){await endSession(false);notice('This session is no longer available. Start a new session to reconnect.');return;}
    } finally {pollRunning=false;if(active()&&target===session)timer=setTimeout(()=>poll(session),failures?Math.min(500*failures,5000):(state?.busy?150:700));}
  }

  // ---- Live screen: its own loop, decode before swapping, never blank on a transient miss.
  async function frameLoop(target) {
    frameLoopRunning = true;
    try {
      while (active() && target === session) {
        if (document.hidden || state?.status !== 'ready') { await sleep(400); continue; }
        const started = performance.now();
        await refreshFrame(target);
        await sleep(Math.max(60, 220 - (performance.now() - started)));
      }
    } finally { frameLoopRunning = false; }
  }
  async function refreshFrame(target) {
    try {
      const frame = await request(endpoint('/screen',target),{},target,8000);
      if (frame.status === 204) { if (!hasFrame) setText(ui['screen-status'],'Waiting for the live screen'); return; }
      const blob = await frame.blob();
      if (target!==session || !active() || !blob.type.startsWith('image/')) return;
      const url = URL.createObjectURL(blob);
      const probe = new Image(); probe.src = url;
      try { await probe.decode(); } catch { URL.revokeObjectURL(url); return; }
      if (target!==session || !active() || state?.status!=='ready') { URL.revokeObjectURL(url); return; }
      const previous = shownFrameURL; shownFrameURL = url; ui.screen.src = url;
      if (!hasFrame) { hasFrame = true; ui.screen.hidden = false; ui['screen-empty'].hidden = true; }
      setText(ui['screen-status'],'Live view');
      if (previous) requestAnimationFrame(()=>requestAnimationFrame(()=>URL.revokeObjectURL(previous)));
    } catch { if (target===session && !hasFrame) setText(ui['screen-status'],'Connecting to the live screen…'); }
  }
  function clearScreen(){hasFrame=false;if(shownFrameURL)URL.revokeObjectURL(shownFrameURL);shownFrameURL=null;ui.screen.removeAttribute('src');ui.screen.hidden=true;ui['screen-empty'].hidden=false;}

  // ---- Voice: one reusable player, bounded lookahead, and a watchdog so a lost event never stalls later replies.
  const voiceQueue = (() => {
    const player = new Audio(); player.preload = 'auto';
    let enabled = prefs.get('beacon.voice') !== 'off', unlocked = false, blocked = false;
    let queue = [], spoken = new Set(), generation = 0, runId = 0, playing = false, stopCurrent = null, utterance = null, onIdle = null;
    let currentText = '', recent = [];
    function remember() { if (currentText) recent.push({text: currentText, at: performance.now()}); currentText = ''; recent = recent.filter(r => performance.now() - r.at < 5000); }
    const status = text => setText(ui['voice-status'], text);
    const idleText = () => enabled ? 'Voice on · Beacon reads each reply aloud.' : 'Voice off · Replies appear as text.';
    function silentWav() {
      const bytes = new Uint8Array(44 + 800), view = new DataView(bytes.buffer), text = (o,s)=>[...s].forEach((c,i)=>bytes[o+i]=c.charCodeAt(0));
      text(0,'RIFF'); view.setUint32(4,36+800,true); text(8,'WAVEfmt '); view.setUint32(16,16,true); view.setUint16(20,1,true); view.setUint16(22,1,true);
      view.setUint32(24,8000,true); view.setUint32(28,8000,true); view.setUint16(32,1,true); view.setUint16(34,8,true); text(36,'data'); view.setUint32(40,800,true);
      bytes.fill(128,44); return new Blob([bytes],{type:'audio/wav'});
    }
    function unlock() {
      // Called inside click handlers: a gesture-started play() lets later replies play without one.
      if (unlocked) { if (blocked) { blocked = false; pump(); } return; }
      unlocked = true;
      // Never interrupt a reply that is already playing: the player is evidently allowed.
      if (playing || !player.paused) return;
      const url = URL.createObjectURL(silentWav());
      player.src = url;
      // Pause only the silent clip; a reply may already have replaced it (AbortError is not a refusal).
      player.play().then(()=>{if(player.src===url)player.pause();URL.revokeObjectURL(url);if(blocked){blocked=false;pump();}},
        e=>{URL.revokeObjectURL(url);if(e?.name==='NotAllowedError')unlocked=false;});
      try { window.speechSynthesis?.getVoices(); } catch {}
    }
    function fetchClip(item) {
      if (!item.audio) item.audio = request(endpoint('/speech?message_id='+encodeURIComponent(item.id)+'&part='+item.part, item.target), {}, item.target, 30000)
        .then(r=>r.blob()).then(b=>b.type.startsWith('audio/') ? b : null).catch(()=>null);
      return item.audio;
    }
    function lookahead() { queue.slice(0,2).forEach(fetchClip); }
    function offer(message) {
      if (spoken.has(message.id)) return;
      spoken.add(message.id);
      if (!enabled || !session) return;
      const parts = Array.isArray(message.parts) && message.parts.length ? message.parts : [message.text || ''];
      parts.forEach((text,part)=>queue.push({id:message.id,part,text,target:session}));
      lookahead(); pump();
    }
    function playBlob(blob) {
      return new Promise(resolve => {
        const url = URL.createObjectURL(blob); let settled = false, watchdog = null;
        const done = result => { if (settled) return; settled = true; clearTimeout(watchdog); player.onended = player.onerror = null; stopCurrent = null; URL.revokeObjectURL(url); resolve(result); };
        stopCurrent = () => done('stopped');
        player.onended = () => done('ok'); player.onerror = () => done('failed');
        player.src = url;
        player.play().then(()=>{
          mark('audio');
          status('Speaking…');
          const seconds = Number.isFinite(player.duration) && player.duration > 0 ? player.duration : 40;
          watchdog = setTimeout(()=>done('ok'), (seconds + 4) * 1000);
        }, e => done(e?.name === 'NotAllowedError' ? 'blocked' : 'failed'));
      });
    }
    function pickVoice() {
      const voices = window.speechSynthesis?.getVoices?.() || [];
      return voices.find(v=>/^en[-_]IN/i.test(v.lang)) || voices.find(v=>/^en[-_]GB/i.test(v.lang)) || voices.find(v=>/^en/i.test(v.lang)) || null;
    }
    function speakText(text) {
      if (!('speechSynthesis' in window) || !('SpeechSynthesisUtterance' in window)) return Promise.resolve('failed');
      return new Promise(resolve => {
        const u = new SpeechSynthesisUtterance(text); const v = pickVoice(); if (v) { u.voice = v; u.lang = v.lang; } else u.lang = 'en-IN';
        let settled = false;
        const done = result => { if (settled) return; settled = true; clearTimeout(watchdog); stopCurrent = null; utterance = null; resolve(result); };
        // Chrome can drop onend for an utterance that is garbage-collected; keep a reference and a timeout.
        const watchdog = setTimeout(()=>done('ok'), 5000 + text.length * 110);
        utterance = u; stopCurrent = () => { window.speechSynthesis.cancel(); done('stopped'); };
        u.onend = () => done('ok'); u.onerror = e => done(e.error === 'not-allowed' ? 'blocked' : 'failed');
        u.onstart = () => mark('audio');
        window.speechSynthesis.resume(); window.speechSynthesis.speak(u);
        status('Speaking with your browser voice…');
      });
    }
    async function pump() {
      if (playing || blocked || !enabled || !queue.length || !active()) return;
      playing = true; const run = ++runId;
      try {
        while (queue.length && enabled && active() && !blocked) {
          const gen = generation, item = queue.shift(); lookahead();
          if (item.target !== session) continue;
          status('Preparing voice…');
          const blob = await fetchClip(item);
          if (gen !== generation) return;
          currentText = item.text;
          let result = blob ? await playBlob(blob) : 'failed';
          if (gen !== generation || result === 'stopped') return;
          if (result === 'failed') result = await speakText(item.text);
          if (gen !== generation || result === 'stopped') return;
          remember();
          if (result === 'blocked') { queue.unshift(item); blocked = true; status('Tap anywhere in this window to turn on sound.'); return; }
          if (result === 'failed') status('Voice is unavailable for this reply. You can read it above.');
        }
      } finally { if (run === runId) { playing = false; if (!blocked && !queue.length) { status(idleText()); onIdle?.(); } } }
    }
    function cancel() {
      generation++; queue = []; playing = false; blocked = false; remember();
      if (stopCurrent) stopCurrent();
      try { player.pause(); } catch {}
      try { window.speechSynthesis?.cancel(); } catch {}
      utterance = null; status(idleText());
    }
    function setEnabled(value) {
      enabled = value; prefs.set('beacon.voice', value ? 'on' : 'off');
      ui.voice.setAttribute('aria-pressed', String(value)); setText(ui.voice, value ? '🔊 Voice on' : '🔇 Voice off');
      if (!value) cancel(); else status(idleText());
    }
    function replay(message) {
      cancel(); spoken.add(message.id);
      const parts = Array.isArray(message.parts) && message.parts.length ? message.parts : [message.text || ''];
      parts.forEach((text,part)=>queue.push({id:message.id,part,text,target:session}));
      lookahead(); pump();
    }
    function reset() { cancel(); spoken = new Set(); }
    return {offer, cancel, unlock, replay, reset, setEnabled, get enabled() { return enabled; },
      get speaking() { return playing || queue.length > 0; }, set onIdle(fn) { onIdle = fn; },
      skip(message) { spoken.add(message.id); },
      // Text Beacon is saying or said moments ago; recognition results lag the audio by a second or two.
      recentSpeech() { const now = performance.now(); return [currentText, ...recent.filter(r => now - r.at < 3500).map(r => r.text)].filter(Boolean).join(' '); }};
  })();

  // ---- Speak instead of typing (browser speech recognition: Chrome/Edge). Talk mode listens all the time,
  // including while Beacon speaks or works: speaking over Beacon stops it at once and runs the new request.
  // Beacon's own voice is kept out by an echo-cancelled microphone track where the browser accepts one,
  // and by ignoring transcripts that only repeat what Beacon just said. Typing always works too.
  const talk = (() => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const languages = {'en-IN':'🗣 English','hi-IN':'🗣 हिन्दी'};
    const STOP_WORDS = /^(stop|stop it|please stop|stop please|wait|ruko|ruk jao|rukiye|bas|bas karo|chup|रुको|रुक जाओ|रुकिए|बस|बस करो|चुप)$/i;
    let lang = languages[prefs.get('beacon.micLang')] ? prefs.get('beacon.micLang') : 'en-IN';
    // Newer recognition (with on-device support) also accepts a MediaStreamTrack; older ones use the default mic.
    let useTrack = typeof Recognition?.available === 'function';
    let recognition = null, listening = false, on = false, restart = null, flushTimer = null;
    let heard = '', typed = null, track = null, quickEnds = 0, lastStart = 0;
    const placeholder = ui.message.getAttribute('placeholder');
    const status = text => setText(ui['voice-status'], text);
    const listeningText = () => lang === 'hi-IN' ? '🎤 सुन रहा हूँ… कभी भी बोलिए, मेरे बोलते समय भी।' : '🎤 Listening… speak any time, even while I am talking.';
    const words = text => (text.toLowerCase().match(/[\p{L}\p{N}]+/gu) || []);
    const pairs = ws => ws.slice(1).map((w, i) => ws[i] + ' ' + w);
    function currentReply() {
      const messages = state?.messages || [], lastUser = messages.map(m=>m.role).lastIndexOf('user');
      return messages.slice(lastUser + 1).filter(m=>m.role==='assistant').map(m=>m.text).join(' ');
    }
    // Echo repeats Beacon's phrases in order, so compare word pairs, not single words: a real question
    // such as "how to change status" shares words with a reply but rarely its word sequence.
    function isEcho(text) {
      const recent = voiceQueue.recentSpeech(); if (!recent) return false;
      const said = words(recent + ' ' + currentReply()), got = words(text);
      if (!got.length) return true;
      if (got.length === 1) return said.includes(got[0]) && !STOP_WORDS.test(got[0]);
      const known = new Set(pairs(said)), heardPairs = pairs(got);
      return heardPairs.filter(p => known.has(p)).length / heardPairs.length > 0.5;
    }
    function paint() {
      ui.mic.hidden = !Recognition; ui['mic-lang'].hidden = !Recognition;
      ui.mic.setAttribute('aria-pressed', String(on)); ui.mic.classList.toggle('listening', on && listening);
      ui.mic.title = on ? 'Listening all the time · tap to turn off' : 'Talk instead of typing';
      ui.message.placeholder = on ? (state?.busy ? 'Listening… speak to change the request' : 'Listening… speak any time')
        : state?.busy ? 'Type to change the request…' : placeholder;
      setText(ui['mic-lang'], languages[lang]);
    }
    async function micTrack() {
      if (!useTrack) return null;
      if (track?.readyState === 'live') return track;
      try { track = (await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}})).getAudioTracks()[0]; }
      catch (e) { track = null; if (e?.name === 'NotAllowedError') throw e; }
      return track;
    }
    function releaseMic() { try { track?.stop(); } catch {} track = null; }
    function flush() {
      clearTimeout(flushTimer); flushTimer = null;
      const text = [typed, heard].map(x => (x || '').trim()).filter(Boolean).join(' ');
      heard = ''; typed = null;
      if (!text) return;
      if (STOP_WORDS.test(text.replace(/[.!?।,]+/g, '').trim())) { ui.message.value = ''; controls(); stop(); return; }
      send(text);
    }
    function onResult(e) {
      let finals = '', interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) { const t = e.results[i][0].transcript; if (e.results[i].isFinal) finals += ' ' + t; else interim += ' ' + t; }
      if (finals.trim() && !isEcho(finals)) { heard += ' ' + finals.trim(); heardAt = Math.round(performance.now()); }
      const live = interim.trim() && !isEcho(interim) ? interim.trim() : '';
      const current = (heard + ' ' + live).trim();
      if (!current) return;
      if (typed === null) typed = ui.message.value.trim();
      // The visitor is speaking: cut Beacon off at once (barge-in).
      if (voiceQueue.speaking && (words(current).length >= 2 || heard.trim())) voiceQueue.cancel();
      ui.message.value = [typed, current].filter(Boolean).join(' '); controls();
      clearTimeout(flushTimer);
      // Send after a short pause, so a question spoken with a breath in the middle is not split in two.
      // Chrome sends a final result only after the visitor pauses, so a short grace period is enough.
      if (heard.trim()) flushTimer = setTimeout(flush, live ? 900 : 300);
    }
    function schedule(ms) { if (on && !restart) restart = setTimeout(() => { restart = null; listen(); }, ms); }
    async function listen() {
      if (!Recognition || listening || !on || !active()) return;
      let input = null;
      try { input = await micTrack(); }
      catch { on = false; paint(); status('Microphone is blocked. Allow it from the address bar, then tap 🎤 again. You can still type.'); return; }
      if (!on || listening || !active()) return;
      const r = new Recognition(); recognition = r;
      r.lang = lang; r.interimResults = true; r.continuous = true; r.maxAlternatives = 1;
      r.onresult = onResult;
      r.onerror = e => {
        if (['not-allowed','service-not-allowed'].includes(e.error)) { on = false; releaseMic(); status('Microphone is blocked. Allow it from the address bar, then tap 🎤 again. You can still type.'); }
        else if (e.error === 'audio-capture') { if (input) useTrack = false; else { on = false; status('No microphone was found. You can still type.'); } }
        else if (e.error === 'network') status('Speech recognition lost its connection; retrying…');
        else if (input && !['no-speech','aborted'].includes(e.error)) useTrack = false;
      };
      r.onend = () => {
        if (recognition !== r) return;
        recognition = null; listening = false;
        if (heard.trim()) flush();
        // Chrome ends continuous recognition periodically; restart, backing off if it keeps ending at once.
        quickEnds = performance.now() - lastStart < 2000 ? quickEnds + 1 : 0;
        paint();
        if (on) schedule(quickEnds > 3 ? 3000 : 250); else releaseMic();
      };
      lastStart = performance.now();
      try {
        if (input) { try { r.start(input); } catch { useTrack = false; r.start(); } } else r.start();
        listening = true;
      } catch { recognition = null; listening = false; schedule(1000); }
      paint();
    }
    function abortRecognition() { if (recognition) { const r = recognition; recognition = null; listening = false; try { r.abort(); } catch {} } }
    function toggle() {
      if (!Recognition) return;
      voiceQueue.unlock();
      if (on) {
        on = false; clearTimeout(restart); restart = null;
        if (heard.trim()) flush(); else { heard = ''; typed = null; }
        abortRecognition(); releaseMic(); paint(); status('Talk mode off. Type, or tap 🎤 to speak.'); return;
      }
      // Tapping the mic means "I want to talk now": stop Beacon's narration first.
      on = true; quickEnds = 0; voiceQueue.cancel(); paint(); status(listeningText());
      listen();
    }
    function shutdown() { on = false; clearTimeout(restart); restart = null; clearTimeout(flushTimer); heard = ''; typed = null; abortRecognition(); releaseMic(); paint(); }
    function switchLanguage() {
      lang = lang === 'en-IN' ? 'hi-IN' : 'en-IN'; prefs.set('beacon.micLang', lang); paint();
      // Restart so the new language applies straight away.
      if (on) { abortRecognition(); status(listeningText()); schedule(150); }
    }
    voiceQueue.onIdle = () => { if (on) status(listeningText()); };
    paint();
    return {toggle, shutdown, switchLanguage, refresh() { paint(); schedule(250); }, get on() { return on; }};
  })();

  async function start() {
    if(starting || session)return;starting=true;error('');notice('');controls();voiceQueue.unlock();
    try {
      const response=await request('/api/sessions',{method:'POST',body:JSON.stringify({parent_origin:parentOrigin})},null);const next=await response.json();
      if(!next.id || !next.token)throw new Error('Beacon returned an incomplete session. Please try again.');
      session={id:next.id,token:next.token};state=next;voiceQueue.reset();rendered.clear();firstRender=true;stepsKey='';lastStateError='';failures=0;
      // Server-side voice preparation starts once it knows the preference.
      await request(endpoint('/voice'),{method:'POST',body:JSON.stringify({enabled:voiceQueue.enabled})}).catch(()=>{});
      render(next);poll(session);
    }
    catch(e){error(e.message || 'Could not connect to Beacon. Check that the demo service is running.');setText(ui.status,'Unable to connect');}
    finally{starting=false;controls();}
  }
  async function send(message) {
    if(!message.trim() || !canSend())return;
    const target=session,text=message.trim(),interrupt=!!state?.busy;
    latency.push({heard:heardAt,sent:Math.round(performance.now()),voice:voiceQueue.enabled});heardAt=null;
    voiceQueue.unlock();voiceQueue.cancel();voiceHold=(state?.messages||[]).filter(m=>m.role==='user').length;sending=true;error('');lastStateError='';controls();
    const post=async body=>{
      try{return await request(endpoint('/turn',target),{method:'POST',body:JSON.stringify(body)},target);}
      catch(e){if(e.status!==429)throw e;await sleep(600);return request(endpoint('/turn',target),{method:'POST',body:JSON.stringify(body)},target);}
    };
    try {
      try{await post(interrupt?{message:text,interrupt:true}:{message:text});}
      catch(e){
        // A demo that started meanwhile, or an older backend without interrupt: stop it, then ask.
        if(!(e.status===409||(interrupt&&e.status===422)))throw e;
        await request(endpoint('/stop',target),{method:'POST'},target);await post({message:text});
      }
      if(target===session){ui.message.value='';render({...state,busy:true});poll(target);}
    }
    catch(e){voiceHold=-1;if(target===session)error(e.message);}
    finally{sending=false;controls();}
  }
  async function endSession(remote=true) {
    if(ending)return;const target=session;ending=true;clearTimeout(timer);talk.shutdown();voiceQueue.cancel();controls();
    if(remote && target){try{await request(endpoint('',target),{method:'DELETE'},target);}catch(e){error('Could not confirm that the session ended. '+e.message);ending=false;controls();poll(target);return;}}
    session=null;state=null;ending=false;voiceQueue.reset();rendered.clear();stepsKey='';clearScreen();ui.activity.hidden=true;setText(ui.status,'Session ended');ui['status-dot'].className='';setText(ui['screen-status'],'Waiting for a session');setText(ui['empty-description'],'Your session has ended. Start a new session to explore again.');notice('');ui.messages.replaceChildren();const p=document.createElement('p');p.className='welcome';p.textContent='Thanks for exploring. Start a new session whenever you’re ready.';ui.messages.append(p);controls();
  }
  async function stop(){if(!session || stopPending)return;voiceQueue.cancel();stopPending=true;controls();try{await request(endpoint('/stop'),{method:'POST'});error('');notice('The current walkthrough was stopped.');}catch(e){error(e.message);}finally{stopPending=false;controls();}}
  ui.start.addEventListener('click',start);ui.end.addEventListener('click',()=>endSession());ui.stop.addEventListener('click',stop);
  $('composer').addEventListener('submit',e=>{e.preventDefault();send(ui.message.value);});ui.message.addEventListener('input',controls);ui.message.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send(ui.message.value);}});
  ui.suggestions.addEventListener('click',e=>{const b=e.target.closest('[data-prompt]');if(b)send(b.dataset.prompt);});
  ui.mic.addEventListener('click',()=>talk.toggle());ui['mic-lang'].addEventListener('click',()=>talk.switchLanguage());
  ui.voice.addEventListener('click',()=>{const value=!voiceQueue.enabled;voiceQueue.setEnabled(value);if(value)voiceQueue.unlock();if(session)request(endpoint('/voice'),{method:'POST',body:JSON.stringify({enabled:value})}).catch(e=>error(e.message));});
  ui.replay.addEventListener('click',()=>{const messages=state?.messages||[];const last=[...messages].reverse().find(m=>m.role==='assistant');if(!last)return;voiceQueue.unlock();if(!voiceQueue.enabled){voiceQueue.setEnabled(true);if(session)request(endpoint('/voice'),{method:'POST',body:JSON.stringify({enabled:true})}).catch(()=>{});}voiceQueue.replay(last);});
  // Any interaction re-enables sound that the browser blocked.
  document.addEventListener('pointerdown',()=>voiceQueue.unlock(),{capture:true});
  $('close').addEventListener('click',async()=>{await endSession();if(session)return;closed=true;if(window.parent!==window)window.parent.postMessage({type:'beacon.close'},parentOrigin);});
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&!starting&&!ending&&!(e.target===ui.message&&ui.message.value)){e.preventDefault();$('close').click();}
    if(e.key==='Tab'&&window.parent!==window){
      const focusable=[...document.querySelectorAll('a[href],button,textarea,input,select,[tabindex]')].filter(el=>!el.disabled&&el.tabIndex>=0&&el.getClientRects().length&&!el.closest('[hidden],[inert]'));
      const first=focusable[0],last=focusable[focusable.length-1];
      if(!first)return;
      if(e.shiftKey&&(document.activeElement===first||document.activeElement===document.body)){e.preventDefault();last.focus();}
      else if(!e.shiftKey&&(document.activeElement===last||document.activeElement===document.body)){e.preventDefault();first.focus();}
    }
  });
  window.addEventListener('pagehide',()=>{closed=true;clearTimeout(timer);talk.shutdown();voiceQueue.cancel();clearScreen();if(session)fetch(endpoint(),{method:'DELETE',headers:{'X-Beacon-Token':session.token},keepalive:true}).catch(()=>{});});
  voiceQueue.setEnabled(voiceQueue.enabled);
  controls();
})();
