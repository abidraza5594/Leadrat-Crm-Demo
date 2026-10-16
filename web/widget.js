(() => {
  'use strict';
  const origin = new URL(document.currentScript.src).origin;
  const style = document.createElement('style');
  style.textContent = '.beacon-launcher{position:fixed;right:28px;bottom:26px;border:0;border-radius:12px;background:#104d46;color:#fff;padding:17px 23px;font:600 15px system-ui;box-shadow:0 8px 30px #123e422a;cursor:pointer;z-index:2147483000}.beacon-launcher:focus-visible{outline:3px solid #dfac56;outline-offset:4px}.beacon-overlay{position:fixed;inset:0;background:#14352ec2;z-index:2147483001;display:grid;place-items:center;padding:28px}.beacon-overlay[hidden]{opacity:0;pointer-events:none;z-index:-2147483647}.beacon-frame{border:0;width:min(1400px,100%);height:min(850px,100%);border-radius:18px;background:#f7f8f4;box-shadow:0 30px 100px #071a2880}@media(max-width:700px){.beacon-overlay{padding:0}.beacon-frame{height:100%;border-radius:0}.beacon-launcher{right:18px;bottom:18px}}';
  document.head.append(style);
  const button = document.createElement('button');
  button.className = 'beacon-launcher'; button.type = 'button'; button.textContent = 'Explore with Beacon ↗'; button.setAttribute('aria-haspopup', 'dialog');
  // While closed, the overlay stays laid out but transparent and inert, so the preloaded window is already
  // rendered and appears in the next frame after a click (display:none would delay its first layout).
  const overlay = document.createElement('div'); overlay.className = 'beacon-overlay'; overlay.hidden = true; overlay.inert = true;
  overlay.setAttribute('role', 'dialog'); overlay.setAttribute('aria-modal', 'true'); overlay.setAttribute('aria-label', 'Beacon live CRM demo');
  let iframe = null; let previousFocus = null; let previousOverflow = '';
  // The demo window loads hidden in the background; a click only shows it and starts the session.
  let frameReady = false, openRequested = false;
  const backgroundState = new Map();
  function containBackground() {
    for (const element of document.body.children) {
      if (element === overlay || backgroundState.has(element)) continue;
      backgroundState.set(element, element.inert); element.inert = true;
    }
  }
  const backgroundObserver = new MutationObserver(containBackground);
  function preload() {
    if (iframe) return;
    iframe = document.createElement('iframe'); iframe.className = 'beacon-frame'; iframe.title = 'Beacon guided CRM demo';
    iframe.src = origin + '/widget.html?preload=1&parent_origin=' + encodeURIComponent(location.origin);
    iframe.allow = 'microphone; autoplay'; iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms');
    frameReady = false; openRequested = false; overlay.append(iframe);
  }
  function requestStart() {
    if (openRequested && frameReady && !overlay.hidden) { openRequested = false; iframe.contentWindow.postMessage({type: 'beacon.open'}, origin); }
  }
  function open() {
    if (!overlay.hidden) return;
    previousFocus = document.activeElement; previousOverflow = document.body.style.overflow;
    preload(); openRequested = true;
    overlay.inert = false; overlay.hidden = false; containBackground();
    backgroundObserver.observe(document.body, {childList:true});
    document.body.style.overflow = 'hidden'; button.setAttribute('aria-expanded','true'); iframe.focus();
    requestStart();
  }
  function close() {
    backgroundObserver.disconnect();
    for (const [element, wasInert] of backgroundState) element.inert = wasInert;
    backgroundState.clear();
    overlay.hidden = true; overlay.inert = true; iframe?.remove(); iframe = null; document.body.style.overflow = previousOverflow;
    button.setAttribute('aria-expanded','false'); previousFocus?.focus();
    // Prepare the next visit straight away.
    setTimeout(preload, 0);
  }
  window.addEventListener('message', event => {
    if (event.origin !== origin || !iframe || event.source !== iframe.contentWindow) return;
    if (event.data?.type === 'beacon.ready') { frameReady = true; requestStart(); }
    else if (event.data?.type === 'beacon.close') close();
  });
  document.addEventListener('focusin', event => {if(!overlay.hidden && !overlay.contains(event.target))iframe?.focus();});
  button.addEventListener('click', open);
  document.addEventListener('click', e => { if (e.target.closest('[data-beacon-open]')) open(); });
  // Hovering or focusing a launcher means a click is likely: load now if the idle preload has not run yet.
  for (const type of ['pointerover', 'focusin']) document.addEventListener(type, e => { if (e.target.closest?.('[data-beacon-open],.beacon-launcher')) preload(); }, {passive: true});
  document.body.append(button, overlay); window.Beacon = Object.freeze({open});
  const idle = window.requestIdleCallback || (fn => setTimeout(fn, 300));
  if (document.readyState === 'complete') idle(preload, {timeout: 1500});
  else window.addEventListener('load', () => idle(preload, {timeout: 1500}), {once: true});
})();
