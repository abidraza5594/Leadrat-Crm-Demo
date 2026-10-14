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
  let pendingRequest = null;
  let registrationOpened = false, registrationSubmitting = false, queuedRegistrationMessage = '';
  let registrationEdited = false;
  let quickReplyKey = '';
  let userEnded = false, reconnectTimer = null, reconnectAttempts = 0;
  function reconnect() {
    if (closed || userEnded || session || reconnectTimer || reconnectAttempts >= 3) return;
    notice('Connecting your workspace…');
    reconnectTimer=setTimeout(()=>{reconnectTimer=null;start();},1000 * 2 ** reconnectAttempts++);
  }
  const rendered = new Map();
  const active = () => !!session && !ending && !closed;
  const ready = () => active() && ['ready','active','login_required'].includes(state?.status) && !state?.busy && !sending && !stopPending;
  // A new question may be sent while Beacon is working; it interrupts the running demonstration.
  const registered = () => !state?.registration_required || !!state?.registration_accepted || state?.registration_status==='created';
  const canSend = () => active() && ['ready','active','login_required'].includes(state?.status) && !sending && !stopPending;
  let voiceHold = -1;
  // Latency marks per turn (performance.now() ms): heard = final speech result, sent, reply shown, audio playing.
  const latency = window.__beaconLatency = [];
  let heardAt = null;
  // Stage timings from the server for this session (used by eval/latency.py); the token itself is not exposed.
  window.__beaconTimings = () => session ? request(endpoint('/timings')).then(r=>r.json()) : Promise.resolve(null);
  const mark = (name) => { const turn = latency[latency.length - 1]; if (turn && turn[name] == null) turn[name] = Math.round(performance.now()); };
  function setText(el, text) { if (el.textContent !== text) el.textContent = text; }
  function setSpeechDraft(text) {
    ui.message.value=text;
    ui.message.setSelectionRange(text.length,text.length);
    ui.message.scrollTop=ui.message.scrollHeight;
    requestAnimationFrame(()=>{if(ui.message.value===text)ui.message.scrollTop=ui.message.scrollHeight;});
  }
  function show(el, text) { setText(el, text || ''); el.hidden = !text; }
  const error = text => show(ui.error, text);
  const notice = text => show(ui.notice, text);
  function controls() {
    $('close').disabled = starting || ending;
    ui.start.hidden = !!session; ui.start.disabled = starting; setText(ui.start, starting ? 'Connecting…' : 'Start a session ↗');
    ui.message.disabled = !canSend(); ui.send.disabled = !canSend() || !ui.message.value.trim(); ui.mic.disabled = !canSend();
    ui.suggestions.hidden = !session; ui.suggestions.querySelectorAll('button').forEach(b=>b.disabled=!canSend());
    ui.end.disabled = !session || ending; ui.stop.disabled = !session || stopPending || !state?.busy;
    ui.replay.disabled = !active() || !state?.messages?.some(m=>m.role==='assistant');
    registrationControls();
    renderQuickReplies();
  }
  function renderQuickReplies() {
    const box=$('quick-replies'), options=state?.quick_replies;
    box.hidden=!(active() && registered() && options && !state?.busy && !sending);
    if(!box.hidden)ui.suggestions.hidden=true;
    const key=JSON.stringify(options || null);
    if(key!==quickReplyKey){
      quickReplyKey=key;
      const list=$('quick-reply-options');list.replaceChildren();
      if(options){
        for(const option of options.options || []){
          const b=document.createElement('button');b.type='button';b.textContent=option.label;
          b.addEventListener('click',()=>{if(state?.quick_replies?.question===options.question && !state?.busy)send(option.message);});list.append(b);
        }
        const custom=document.createElement('button');custom.type='button';custom.className='quick-reply-secondary';custom.textContent=options.custom_label;
        custom.addEventListener('click',()=>ui.message.focus());list.append(custom);
        const skip=document.createElement('button');skip.type='button';skip.className='quick-reply-secondary';skip.textContent='Skip for now';
        skip.addEventListener('click',()=>{if(state?.quick_replies?.question===options.question && !state?.busy)send(options.skip_message);});list.append(skip);
      }
    }
    box.querySelectorAll('button').forEach(b=>b.disabled=!canSend() || !!state?.busy);
  }
  function registrationControls() {
    const form=$('visitor-form'), busy=registrationSubmitting || state?.registration_status==='saving';
    form.hidden=!active() || busy || !registrationOpened;
    $('registration-start').hidden=!active() || registered() || registrationOpened;
    $('registration-start').disabled=!canSend();
    form.querySelectorAll('input,button').forEach(el=>el.disabled=busy);
    form.querySelector('button[type="submit"]').disabled=busy;
    setText($('visitor-status'),busy?'Saving your details…':registrationEdited?'Details updated. Select Save to continue.':state?.registration_status==='review_required'?'We couldn’t confirm this number. Enter a different number, or contact support.':state?.registration_status==='duplicate'?'This number is already registered. Enter a different phone number.':state?.registration_status==='failed'?'Please check the details above and try again.':'');
    show($('registration-question'),queuedRegistrationMessage?'Your request: '+queuedRegistrationMessage:'');
    const captureError=state?.registration_error;
    $('registration-notice').hidden=!active() || busy || !captureError || registrationOpened;
    setText($('registration-notice-text'),busy?'':captureError || '');
    $('registration-retry').hidden=busy || !captureError;
  }
  function openRegistration(message='') {
    registrationOpened=true;
    if(message)queuedRegistrationMessage=message;
    controls();
    $('visitor-form').scrollIntoView({block:'nearest',behavior:'smooth'});
    if(!registrationSubmitting && state?.registration_status!=='saving')$('visitor-form').elements.name.focus();
  }
  async function request(path, options = {}, target = session, timeoutMs = 15000) {
    const controller = new AbortController(); const timeout = setTimeout(()=>controller.abort(), timeoutMs);
    try {
      const response = await fetch(path,{...options,signal:controller.signal,headers:{...(options.body?{'Content-Type':'application/json'}:{}),...(target?{'X-Beacon-Token':target.token}:{}),...options.headers}});
      if (!response.ok) {
        let detail = '', fieldErrors={}; try {
          const data = await response.json();
          if(Array.isArray(data.detail)) {
            const labels={phone:'Check the phone number and selected country.',email:'Enter a valid email address.',name:'Enter a full name between 2 and 75 characters.'};
            for(const item of data.detail){const field=item.loc?.at(-1);if(labels[field])fieldErrors[field]=labels[field];}
            detail=Object.values(fieldErrors).join(' ') || 'Please check the information you entered.';
          } else detail=typeof data.detail === 'string' ? data.detail : data.message || '';
        } catch {}
        const e = new Error(detail || (response.status===409 ? 'Another session or action is already running. Please wait and try again.' : 'Beacon could not complete that request. Please try again.'));
        e.status = response.status;e.fieldErrors=fieldErrors; throw e;
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
      // Acknowledgements ("Let me check that for you.") are voice only.
      if (m.kind === 'ack') continue;
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
    const label = {reconnecting:'Reconnecting your demo',ready:'Ready to explore',active:'Ready to explore',login_required:'Waiting for CRM sign-in',starting:'Preparing workspace',initializing:'Preparing workspace',stopped:'Walkthrough stopped',error:'Session needs attention',ended:'Session ended',closed:'Session ended'}[next.status] || 'Preparing workspace';
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
      messages.forEach((m,i)=>{ if (m.role==='assistant') { if (i < lastUser) voiceQueue.skip(m); else { voiceQueue.offer(m); if (m.kind !== 'ack') mark('shown'); } } });
    }
    renderSteps(Array.isArray(next.steps) ? next.steps : []);
    if (next.status === 'login_required') {
      // Preserve the last verified preview while authentication recovers.
      setText(ui['screen-status'], 'Waiting for CRM sign-in');
    }
    controls();
    talk.refresh();
    if(registered() && queuedRegistrationMessage && canSend()) {
      const question=queuedRegistrationMessage;queuedRegistrationMessage='';
      queueMicrotask(()=>send(question));
    }
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
      failures++;setText(ui['screen-status'],'Reconnecting…');
      if(failures>=3)error(e.message || 'Unable to reach Beacon. Check that the demo service is running.');
      if([401,403,404,410].includes(e.status)){
        await endSession(false);
        if([404,410].includes(e.status))reconnect();
        else notice('Access to this session was refused. Please check the connection settings.');
        return;
      }
    } finally {pollRunning=false;if(active()&&target===session)timer=setTimeout(()=>poll(session),failures?Math.min(500*failures,5000):(state?.busy?100:300));}
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
    const canStream = () => state?.tts_provider==='edge' && window.MediaSource?.isTypeSupported('audio/mpeg');
    // The server already prepares upcoming parts; avoid duplicate buffered downloads when streaming.
    function lookahead() { if(!canStream())queue.slice(0,2).forEach(fetchClip); }
    function offer(message) {
      if (spoken.has(message.id)) return;
      spoken.add(message.id);
      if (!enabled || !session) return;
      const parts = Array.isArray(message.parts) && message.parts.length ? message.parts : [message.text || ''];
      parts.forEach((text,part)=>queue.push({id:message.id,part,text,target:session,kind:message.kind}));
      lookahead(); pump();
    }
    let currentKind = null;
    function playStream(item) {
      return new Promise(resolve => {
        const controller=new AbortController(), source=new MediaSource(), url=URL.createObjectURL(source);
        let settled=false, started=false, watchdog=null, reader=null;
        const done=result=>{
          if(settled)return;
          settled=true;clearTimeout(watchdog);controller.abort();reader?.cancel().catch(()=>{});
          player.onended=player.onerror=player.onplaying=player.ontimeupdate=null;
          player.pause();player.removeAttribute('src');player.load();
          stopCurrent=null;URL.revokeObjectURL(url);
          // Never repeat a partially spoken reply through the fallback voice.
          resolve(result==='failed' && started?'partial':result);
        };
        const arm=()=>{clearTimeout(watchdog);watchdog=setTimeout(()=>done('failed'),20000);};
        stopCurrent=()=>done('stopped');
        player.onended=()=>done('ok');player.onerror=()=>done('failed');
        player.onplaying=()=>{started=true;mark('audio');if(currentKind!=='ack')mark('answer_audio');status('Speaking…');arm();};
        player.ontimeupdate=arm;
        const opened=new Promise(resolveOpen=>source.addEventListener('sourceopen',resolveOpen,{once:true}));
        const aborted=new Promise((_,reject)=>controller.signal.addEventListener('abort',()=>reject(new DOMException('Stopped','AbortError')),{once:true}));
        player.src=url;arm();
        (async()=>{
          try {
            const response=await fetch(endpoint('/speech?message_id='+encodeURIComponent(item.id)+'&part='+item.part+'&stream=true',item.target),{
              headers:{'X-Beacon-Token':item.target.token},signal:controller.signal});
            if(!response.ok || !response.body || !response.headers.get('content-type')?.startsWith('audio/'))throw new Error('No audio');
            await Promise.race([opened,aborted]);
            if(settled)return;
            const buffer=source.addSourceBuffer('audio/mpeg');
            reader=response.body.getReader();let requestedPlay=false;
            while(!settled){
              const {value,done:complete}=await reader.read();
              if(complete)break;
              arm();
              await Promise.race([new Promise((resolveAppend,rejectAppend)=>{
                const cleanup=()=>{buffer.removeEventListener('updateend',updated);buffer.removeEventListener('error',failed);};
                const updated=()=>{cleanup();resolveAppend();};
                const failed=()=>{cleanup();rejectAppend(new Error('Invalid audio'));};
                buffer.addEventListener('updateend',updated);buffer.addEventListener('error',failed);
                try{buffer.appendBuffer(value);}catch(e){cleanup();rejectAppend(e);}
              }),aborted]);
              if(settled)return;
              if(!requestedPlay){requestedPlay=true;player.play().catch(e=>done(e?.name==='NotAllowedError'?'blocked':'failed'));}
            }
            if(!settled){if(!requestedPlay)throw new Error('Empty audio');source.endOfStream();}
          } catch {if(!settled)done('failed');}
        })();
        // Cancellation can happen before any awaited operation subscribes to this promise.
        aborted.catch(()=>{});
      });
    }
    function playBlob(blob) {
      return new Promise(resolve => {
        const url = URL.createObjectURL(blob); let settled = false, watchdog = null;
        const done = result => { if (settled) return; settled = true; clearTimeout(watchdog); player.onended = player.onerror = null; stopCurrent = null; URL.revokeObjectURL(url); resolve(result); };
        stopCurrent = () => done('stopped');
        player.onended = () => done('ok'); player.onerror = () => done('failed');
        player.src = url;
        player.play().then(()=>{
          mark('audio'); if (currentKind !== 'ack') mark('answer_audio');
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
          currentText = item.text; currentKind = item.kind || null;
          let result;
          if(canStream())result=await playStream(item);
          else {
            const blob=await fetchClip(item);
            if(gen!==generation)return;
            result=blob?await playBlob(blob):'failed';
          }
          if (gen !== generation || result === 'stopped') return;
          if (result === 'failed' && state?.tts_provider!=='soniox') result = await speakText(item.text);
          if (gen !== generation || result === 'stopped') return;
          remember();
          if (result === 'blocked') { queue.unshift(item); blocked = true; status('Tap anywhere in this window to turn on sound.'); return; }
          if (result === 'failed' || result === 'partial') status('Voice is unavailable for this reply. You can read it above.');
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

  // ---- Soniox streaming speech recognition. No browser recognition fallback.
  const talk = (() => {
    let on=false, listening=false, lang='en', typed=null;
    const status=t=>setText(ui['voice-status'],t);
    function paint(){
      ui.mic.setAttribute('aria-pressed',String(on));ui.mic.classList.toggle('listening',listening);
      ui.mic.title=on?'Tap to finish speaking':'Speak with Soniox';
      setText(ui['mic-lang'],lang==='en'?'🗣 English':'🗣 हिन्दी');
    }
    function echo(text){
      const recent=voiceQueue.recentSpeech().toLowerCase();
      return text.length>12 && recent.includes(text.toLowerCase());
    }
    const input=new window.BeaconSonioxInput({
      getKey:async()=>{const target=session;const result=await request(endpoint('/speech-key',target),{method:'POST'},target);if(target!==session)throw new Error('Session ended');return result.json();},
      onState:value=>{on=!['off'].includes(value);listening=value==='listening';paint();if(value==='listening')status('Listening with Soniox…');},
      onError:status,
      onText:text=>{if(!text||echo(text))return;if(typed===null)typed=ui.message.value.trim();if(voiceQueue.speaking)voiceQueue.cancel();setSpeechDraft([typed,text].filter(Boolean).join(' '));controls();},
      onUtterance:text=>{
        if(!text||echo(text))return;heardAt=Math.round(performance.now());
        const answer=[typed,text].filter(Boolean).join(' ');typed=null;
        if($('speech-auto-send')?.checked){ui.message.value='';send(answer);}
        else {setSpeechDraft(answer);controls();status('Check the words, then press Send.');}
      }
    });
    return {get on(){return on;},toggle(){
      if(on){input.stop();return;}
      if(!active())return;
      if(!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder){status('This browser cannot record audio. Please type.');return;}
      typed=null;voiceQueue.cancel();input.start(lang);
    },shutdown(){typed=null;input.abort();},switchLanguage(){lang=lang==='en'?'hi':'en';if(on)input.abort();paint();},refresh:paint};
  })();

  async function start() {
    if(starting || session || closed || userEnded)return;
    clearTimeout(reconnectTimer);reconnectTimer=null;
    starting=true;error('');notice('');controls();voiceQueue.unlock();
    try {
      const response=await request('/api/sessions',{method:'POST',body:JSON.stringify({parent_origin:parentOrigin})},null,60000);const next=await response.json();
      if(!next.id || !next.token)throw new Error('Beacon returned an incomplete session. Please try again.');
      if(closed || userEnded){
        await request(endpoint('',next),{method:'DELETE'},next).catch(()=>{});return;
      }
      reconnectAttempts=0;
      session={id:next.id,token:next.token};state=next;voiceQueue.reset();rendered.clear();firstRender=true;stepsKey='';lastStateError='';failures=0;
      pendingRequest=null;
      registrationOpened=false;registrationSubmitting=false;queuedRegistrationMessage='';
      registrationEdited=false;
      // Server-side voice preparation starts once it knows the preference.
      request(endpoint('/voice'),{method:'POST',body:JSON.stringify({enabled:voiceQueue.enabled})}).catch(()=>{});
      render(next);
      if(!frameLoopRunning)frameLoop(session);
      poll(session);
    }
    catch(e){error(e.message || 'Could not connect to Beacon. Check that the demo service is running.');setText(ui.status,'Unable to connect');if(![401,403,409].includes(e.status))reconnect();}
    finally{starting=false;controls();}
  }
  async function send(message) {
    if(!message.trim() || !canSend())return;
    if(!registered()){openRegistration(message.trim());ui.message.value='';controls();return;}
    const target=session,text=message.trim(),interrupt=!!state?.busy;
    // A response can time out after the server accepted it. Reuse the identifier on retry.
    if (!pendingRequest || pendingRequest.text!==text) pendingRequest={text,id:crypto.randomUUID()};
    const requestId=pendingRequest.id;
    latency.push({heard:heardAt,sent:Math.round(performance.now()),voice:voiceQueue.enabled});heardAt=null;
    voiceQueue.unlock();voiceQueue.cancel();voiceHold=(state?.messages||[]).filter(m=>m.role==='user').length;sending=true;error('');lastStateError='';controls();
    const post=async body=>{
      const payload=JSON.stringify({...body,request_id:requestId});
      try{return await request(endpoint('/turn',target),{method:'POST',body:payload},target);}
      catch(e){if(e.status!==429)throw e;await sleep(600);return request(endpoint('/turn',target),{method:'POST',body:payload},target);}
    };
    try {
      try{await post(interrupt?{message:text,interrupt:true}:{message:text});}
      catch(e){
        // A demo that started meanwhile, or an older backend without interrupt: stop it, then ask.
        if(!(e.status===409||(interrupt&&e.status===422)))throw e;
        await request(endpoint('/stop',target),{method:'POST'},target);await post({message:text});
      }
      if(target===session){pendingRequest=null;ui.message.value='';render({...state,busy:true});poll(target);}
    }
    catch(e){voiceHold=-1;if(target===session)error(e.message);}
    finally{sending=false;controls();}
  }
  async function endSession(remote=true) {
    if(remote){userEnded=true;clearTimeout(reconnectTimer);reconnectTimer=null;}
    if(ending)return;const target=session;ending=true;clearTimeout(timer);talk.shutdown();voiceQueue.cancel();controls();
    if(remote && target){try{await request(endpoint('',target),{method:'DELETE'},target);}catch(e){error('Could not confirm that the session ended. '+e.message);ending=false;controls();poll(target);return;}}
    session=null;state=null;ending=false;voiceQueue.reset();rendered.clear();stepsKey='';clearScreen();ui.activity.hidden=true;setText(ui.status,'Session ended');ui['status-dot'].className='';setText(ui['screen-status'],'Waiting for a session');setText(ui['empty-description'],'Your session has ended. Start a new session to explore again.');notice('');ui.messages.replaceChildren();const p=document.createElement('p');p.className='welcome';p.textContent='Thanks for exploring. Start a new session whenever you’re ready.';ui.messages.append(p);controls();
  }
  async function stop(){if(!session || stopPending)return;voiceQueue.cancel();stopPending=true;controls();try{await request(endpoint('/stop'),{method:'POST'});error('');notice('The current walkthrough was stopped.');}catch(e){error(e.message);}finally{stopPending=false;controls();}}
  ui.start.addEventListener('click',()=>{userEnded=false;reconnectAttempts=0;start();});ui.end.addEventListener('click',()=>endSession());ui.stop.addEventListener('click',stop);
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
  const visitorPhone=window.BeaconPhoneField($('visitor-phone'),$('phone-error'));
  function registrationEdit(){
    registrationEdited=true;
    error('');
    controls();
  }
  $('visitor-form').addEventListener('input',registrationEdit);
  $('visitor-phone').addEventListener('countrychange',registrationEdit);
  $('registration-start').addEventListener('click',()=>openRegistration());
  $('registration-retry').addEventListener('click',()=>openRegistration());
  $('visitor-form').addEventListener('submit',async e=>{
    e.preventDefault();if(!session || registrationSubmitting || ['saving','created'].includes(state?.registration_status) || !e.currentTarget.reportValidity())return;
    const form=e.currentTarget;const fields=new FormData(form);
    const target=session;
    // Hide the form only after local validation; never claim the CRM has saved yet.
    registrationSubmitting=true;error('');lastStateError='';
    try {
      const number=await visitorPhone.getNumber();
      if(!number)return;
      registrationEdited=false;
      registrationOpened=false;controls();
      fields.set('phone',number);
      const response=await request(endpoint('/visitor',target),{method:'POST',body:JSON.stringify(Object.fromEntries(fields))},target);
      const result=await response.json();
      if(target===session){
        registrationSubmitting=false;
        if(!result.accepted)registrationOpened=true;
        render({...state,registration_status:result.status || 'saving',registration_accepted:!!result.accepted,registration_error:null});
        ui.message.focus();
        poll(target);
      }
    }
    catch(e){if(target===session){registrationOpened=true;error(e.message);if(e.fieldErrors?.phone)visitorPhone.showError(e.fieldErrors.phone);}}
    finally{if(target===session){registrationSubmitting=false;controls();}}
  });
  voiceQueue.setEnabled(voiceQueue.enabled);
  controls();
  start();
})();
