"""Visible step-by-step guidance on the live CRM screen.

Before Beacon clicks a control it draws a labelled box around it, says the step ("Step 2: Click Status"),
pauses so the visitor can see where it is, and only then clicks. Controls that are only pointed out get the
same box without a click. The box is a pointer-events:none overlay: it never changes or intercepts the CRM.
"""
import asyncio
import contextvars
import os

DWELL = float(os.getenv('GUIDE_DWELL_MS', '1400')) / 1000
# (notify callback, step counter) for the running turn; each turn starts at step 1.
_turn = contextvars.ContextVar('beacon_guide', default=None)

def start_turn(notify):
    _turn.set({'notify': notify, 'step': 0})

DRAW = """({x, y, w, h, caption}) => {
  let box = document.getElementById('beacon-guide-box');
  if (!box) {
    box = document.createElement('div'); box.id = 'beacon-guide-box';
    const tag = document.createElement('div'); tag.id = 'beacon-guide-tag'; box.append(tag);
    document.documentElement.append(box);
  }
  Object.assign(box.style, {position:'fixed', left:(x-6)+'px', top:(y-6)+'px', width:(w+12)+'px', height:(h+12)+'px',
    border:'3px solid #f5a623', borderRadius:'8px', boxShadow:'0 0 0 4000px rgba(10,30,40,.28), 0 0 18px #f5a623',
    pointerEvents:'none', zIndex:'2147483647', transition:'left .15s ease, top .15s ease, width .15s ease, height .15s ease'});
  const tag = box.firstChild; tag.textContent = caption;
  const above = y > 40;
  // Reset both edges: the previous step may have placed the label on the other side.
  Object.assign(tag.style, {position:'absolute', left:'-3px', top: above ? 'auto' : 'calc(100% + 6px)', bottom: above ? 'calc(100% + 6px)' : 'auto', whiteSpace:'nowrap',
    background:'#f5a623', color:'#1d2a30', font:'600 13px system-ui, sans-serif', padding:'5px 9px', borderRadius:'6px',
    boxShadow:'0 2px 8px rgba(0,0,0,.25)'});
}"""
CLEAR = "() => document.getElementById('beacon-guide-box')?.remove()"

async def draw(target, caption):
    try:
        await target.scroll_into_view_if_needed(timeout=3000)
        box = await target.bounding_box()
        if not box: return False
        await target.page.evaluate(DRAW, {'x': box['x'], 'y': box['y'], 'w': box['width'], 'h': box['height'], 'caption': caption})
        return True
    except Exception:
        # Guidance is presentation only; it must never break the demo step itself.
        return False

async def clear(page):
    try: await page.evaluate(CLEAR)
    except Exception: pass

def _next_step(caption):
    turn = _turn.get()
    if not turn: return caption
    turn['step'] += 1
    text = f"Step {turn['step']}: {caption}."
    if turn['notify']: turn['notify'](text)
    return text

async def click(target, caption):
    """Point at the control, narrate the step, pause, then click."""
    label = _next_step(caption)
    if await draw(target, label): await asyncio.sleep(DWELL)
    await clear(target.page)
    await target.click()

async def point(target, caption):
    """Point at a control without clicking; the box stays until the next step."""
    if await draw(target, caption): await asyncio.sleep(DWELL * 0.6)
