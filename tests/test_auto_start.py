import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright

def test_auto_start_reconnect_and_explicit_end():
 async def run():
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(channel='chrome',headless=True)
   page=await browser.new_page();created=[];expired=False;turns=[]
   voice_release=asyncio.Event();screen_requested=asyncio.Event()
   await page.add_init_script("localStorage.setItem('beacon.voice','off')")
   async def route(r):
    nonlocal expired
    path=r.request.url.split('http://localhost:9876')[-1].split('?')[0]
    if path.startswith('/api/'):
     if path.endswith('/voice'):await voice_release.wait()
     if path.endswith('/screen'):screen_requested.set()
     if path=='/api/sessions' and r.request.method=='POST':created.append(str(len(created)+1))
     if path.endswith('/turn'):turns.append(r.request.post_data)
     if r.request.method=='DELETE' or path.endswith('/screen'):
      await r.fulfill(status=204);return
     if expired and path=='/api/sessions/1':
      await r.fulfill(status=404,content_type='application/json',body='{"detail":"Session not found"}');return
     snap={'id':created[-1],'token':'test','status':'ready','busy':False,'messages':[],'steps':[]}
     await r.fulfill(content_type='application/json',body=json.dumps(snap));return
    f=Path('web')/path.lstrip('/')
    await r.fulfill(content_type='text/html' if f.suffix=='.html' else 'text/javascript' if f.suffix=='.js' else 'text/css',body=f.read_text('utf8'))
   await page.route('http://localhost:9876/**',route)
   await page.goto('http://localhost:9876/widget.html')
   # A stalled voice setup must not hold back the live preview.
   await asyncio.wait_for(screen_requested.wait(),3)
   voice_release.set()
   await page.locator('#message').wait_for()
   await page.wait_for_function("!document.getElementById('message').disabled")
   assert created==['1']
   async with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/api/sessions')):
    expired=True
   await page.wait_for_function("!document.getElementById('message').disabled")
   assert created==['1','2'] and not turns
   await page.locator('#end').click()
   await page.wait_for_timeout(1600)
   assert created==['1','2'] and await page.locator('#start').is_visible()
   await browser.close()
 asyncio.run(run())
