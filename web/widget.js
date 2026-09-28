(() => {
  'use strict';
  const origin = new URL(document.currentScript.src).origin;
  const style = document.createElement('style');
  style.textContent = '.beacon-launcher{position:fixed;right:28px;bottom:26px;border:0;border-radius:12px;background:#104d46;color:#fff;padding:17px 23px;font:600 15px system-ui;box-shadow:0 8px 30px #123e422a;cursor:pointer;z-index:2147483000}.beacon-launcher:focus-visible{outline:3px solid #dfac56;outline-offset:4px}.beacon-overlay{position:fixed;inset:0;background:#14352ec2;z-index:2147483001;display:grid;place-items:center;padding:28px}.beacon-overlay[hidden]{display:none}.beacon-frame{border:0;width:min(1400px,100%);height:min(850px,100%);border-radius:18px;background:#f7f8f4;box-shadow:0 30px 100px #071a2880}@media(max-width:700px){.beacon-overlay{padding:0}.beacon-frame{height:100%;border-radius:0}.beacon-launcher{right:18px;bottom:18px}}';
  document.head.append(style);
  const button = document.createElement('button');
  button.className = 'beacon-launcher'; button.type = 'button'; button.textContent = 'Explore with Beacon ↗'; button.setAttribute('aria-haspopup', 'dialog');
  const overlay = document.createElement('div'); overlay.className = 'beacon-overlay'; overlay.hidden = true;
  overlay.setAttribute('role', 'dialog'); overlay.setAttribute('aria-modal', 'true'); overlay.setAttribute('aria-label', 'Beacon live CRM demo');
  let iframe = null; let previousFocus = null; let previousOverflow = '';
  const backgroundState = new Map();
  function containBackground() {
    for (const element of document.body.children) {
      if (element === overlay || backgroundState.has(element)) continue;
      backgroundState.set(element, element.inert); element.inert = true;
    }
  }
  const backgroundObserver = new MutationObserver(containBackground);
  function open() {
    if (!overlay.hidden) return;
    previousFocus = document.activeElement; previousOverflow = document.body.style.overflow;
    iframe = document.createElement('iframe'); iframe.className = 'beacon-frame'; iframe.title = 'Beacon guided CRM demo';
    iframe.src = origin + '/widget.html?parent_origin=' + encodeURIComponent(location.origin);
    iframe.allow = 'microphone; autoplay'; iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms');
    overlay.append(iframe); overlay.hidden = false; containBackground();
    backgroundObserver.observe(document.body, {childList:true});
    document.body.style.overflow = 'hidden'; button.setAttribute('aria-expanded','true'); iframe.focus();
  }
  function close() {
    backgroundObserver.disconnect();
    for (const [element, wasInert] of backgroundState) element.inert = wasInert;
    backgroundState.clear();
    overlay.hidden = true; iframe?.remove(); iframe = null; document.body.style.overflow = previousOverflow;
    button.setAttribute('aria-expanded','false'); previousFocus?.focus();
  }
  window.addEventListener('message', event => { if (event.origin === origin && event.source === iframe?.contentWindow && event.data?.type === 'beacon.close') close(); });
  document.addEventListener('focusin', event => {if(!overlay.hidden && !overlay.contains(event.target))iframe?.focus();});
  button.addEventListener('click', open);
  document.addEventListener('click', e => { if (e.target.closest('[data-beacon-open]')) open(); });
  document.body.append(button, overlay); window.Beacon = Object.freeze({open});
})();
