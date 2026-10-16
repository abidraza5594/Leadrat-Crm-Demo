"""The website preloads the demo window; only a click starts a session (real browser, stubbed API)."""
import asyncio,json,mimetypes
from pathlib import Path
from playwright.async_api import async_playwright

HOST='http://localhost:9877'
WIDGET='http://localhost:9876'

def test_preloaded_window_starts_session_only_when_opened():
 async def run():
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(channel='chrome',headless=True)
   page=await browser.new_page();created=[];deleted=[]
   await page.add_init_script("try{localStorage.setItem('beacon.voice','off')}catch{}")
   async def host(r):
    await r.fulfill(content_type='text/html',body='<!doctype html><button data-beacon-open>Start exploring</button>'
      '<script src="'+WIDGET+'/widget.js"></script>')
   async def widget(r):
    path=r.request.url.split(WIDGET)[-1].split('?')[0]
    if path.startswith('/api/'):
     if path=='/api/sessions' and r.request.method=='POST':created.append(json.loads(r.request.post_data))
     if r.request.method=='DELETE':deleted.append(path);await r.fulfill(status=204);return
     if path.endswith('/screen'):await r.fulfill(status=204);return
     snap={'id':str(len(created)),'token':'test','status':'ready','busy':False,'messages':[],'steps':[]}
     await r.fulfill(content_type='application/json',body=json.dumps(snap));return
    f=Path('web')/path.lstrip('/')
    await r.fulfill(content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream',body=f.read_bytes())
   await page.route(HOST+'/**',host);await page.route(WIDGET+'/**',widget)
   await page.goto(HOST+'/')
   # Loaded while the visitor reads the page, without starting a session.
   await page.wait_for_function("document.querySelector('iframe.beacon-frame')?.src.includes('preload=1')")
   frame=page.frame_locator('iframe.beacon-frame')
   await frame.locator('#start').wait_for(state='attached')
   await page.wait_for_timeout(300)
   assert created==[] and await page.evaluate("document.querySelector('.beacon-overlay').hidden")
   # Laid out but transparent and inert: no clicks or focus reach the waiting window.
   assert await page.evaluate("(o=>getComputedStyle(o).opacity==='0' && o.inert)(document.querySelector('.beacon-overlay'))")
   await page.mouse.click(700,400)
   assert created==[]
   started=asyncio.get_running_loop().time()
   await page.click('[data-beacon-open]')
   await page.wait_for_function("!document.querySelector('.beacon-overlay').hidden")
   await frame.locator('#message').wait_for()
   for _ in range(100):
    if created:break
    await asyncio.sleep(.01)
   assert len(created)==1 and created[0]['voice'] is False
   assert asyncio.get_running_loop().time()-started<1.5
   # Closing ends the session and prepares the next window, which waits for another click.
   await frame.locator('#close').click()
   await page.wait_for_function("document.querySelector('.beacon-overlay').hidden")
   assert deleted==['/api/sessions/1']
   await page.wait_for_function("document.querySelector('iframe.beacon-frame')?.src.includes('preload=1')")
   await page.wait_for_timeout(300)
   assert len(created)==1
   await browser.close()
 asyncio.run(run())
