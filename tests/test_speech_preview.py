import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright

def test_speech_preview_and_optional_auto_send():
 async def run():
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(channel='chrome',headless=True)
   page=await browser.new_page();sent=[]
   await page.add_init_script('''localStorage.setItem('beacon.voice','off');
    window.SpeechRecognition=class {start(){window.rec=this;}abort(){} };''')
   snap={'id':'test','token':'test-token','status':'ready','busy':False,'messages':[],'steps':[]}
   async def route(r):
    path=r.request.url.split('http://localhost:9876')[-1].split('?')[0]
    if path.startswith('/api/'):
     if path.endswith('/turn'):sent.append(r.request.post_data_json)
     if path.endswith('/screen'):await r.fulfill(status=204);return
     await r.fulfill(content_type='application/json',body=json.dumps(snap));return
    file=Path('web')/path.lstrip('/')
    await r.fulfill(content_type='text/html' if file.suffix=='.html' else 'text/javascript' if file.suffix=='.js' else 'text/css',body=file.read_text('utf8'))
   await page.route('http://localhost:9876/**',route)
   await page.goto('http://localhost:9876/widget.html')
   await page.locator('#mic').click()
   await page.wait_for_function('window.rec')
   async def say(text):
    await page.evaluate('text=>{const r=[{transcript:text,confidence:0.8}];r.isFinal=true;window.rec.onresult({resultIndex:0,results:[r]});}',text)
   await say('twenty thousand')
   await page.wait_for_timeout(1400)
   assert await page.locator('#message').input_value()=='twenty thousand'
   assert not sent
   await page.locator('#message').fill('20k')
   async with page.expect_response('**/turn'):
    await page.locator('#send').click()
   assert sent[-1]['message']=='20k'
   await page.wait_for_timeout(600)
   await page.locator('#speech-auto-send').check()
   await say('show leads');await page.wait_for_timeout(1500)
   assert sent[-1]['message']=='show leads' and len(sent)==2
   await browser.close()
 asyncio.run(run())

