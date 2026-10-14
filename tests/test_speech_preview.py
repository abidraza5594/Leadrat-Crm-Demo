import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright

def test_speech_preview_and_optional_auto_send():
 async def run():
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(channel='chrome',headless=True)
   page=await browser.new_page();sent=[]
   await page.add_init_script('''localStorage.setItem('beacon.voice','off');
    navigator.mediaDevices.getUserMedia=async constraints=>{window.micConstraints=constraints;return {getTracks:()=>[{stop(){}}]};};
    window.MediaRecorder=class {static isTypeSupported(){return true;}start(){this.state='recording';}stop(){this.state='inactive';this.onstop?.();}};
    window.WebSocket=class {static OPEN=1;constructor(url,protocols){window.rec=this;this.readyState=1;this.protocols=protocols;setTimeout(()=>this.onopen?.(),0);}send(){}close(){this.readyState=3;} };
    window.SpeechRecognition=class {constructor(){throw new Error('Browser recognition must not be used');}};''')
   snap={'id':'test','token':'test-token','status':'ready','busy':False,'messages':[],'steps':[]}
   async def route(r):
    path=r.request.url.split('http://localhost:9876')[-1].split('?')[0]
    if path.startswith('/api/'):
     if path.endswith('/speech-key'):
      await r.fulfill(content_type='application/json',body=json.dumps({'api_key':'temporary','url':'wss://stt-rt.soniox.com/transcribe-websocket','model':'stt-rt-v5','max_seconds':115}));return
     if path.endswith('/turn'):sent.append(r.request.post_data_json)
     if path.endswith('/screen'):await r.fulfill(status=204);return
     await r.fulfill(content_type='application/json',body=json.dumps(snap));return
    file=Path('web')/path.lstrip('/')
    import mimetypes
    await r.fulfill(content_type=mimetypes.guess_type(str(file))[0] or 'application/octet-stream',body=file.read_bytes())
   await page.route('http://localhost:9876/**',route)
   await page.goto('http://localhost:9876/widget.html')
   await page.locator('#mic').click()
   await page.wait_for_function('window.rec')
   constraints=await page.evaluate('window.micConstraints.audio')
   assert constraints['noiseSuppression'] and constraints['echoCancellation']
   assert constraints['autoGainControl'] is False and constraints['channelCount']==1
   async def say(text):
    await page.evaluate('text=>window.rec.onmessage({data:JSON.stringify({tokens:[{text,is_final:true},{text:"<end>",is_final:true}]})})',text)
   await say('twenty thousand')
   await page.wait_for_timeout(1400)
   assert await page.locator('#message').input_value()=='twenty thousand'
   assert not sent
   long_question=('Please explain how my sales team can manage leads and schedule site visits. '*18)+'final spoken words'
   await say(long_question)
   await page.wait_for_function("document.getElementById('message').value.endsWith('final spoken words')")
   await page.locator('#message').focus()
   await page.wait_for_function("(()=>{const e=document.getElementById('message');return e.scrollTop>0 && e.scrollHeight-e.clientHeight-e.scrollTop<2;})()")
   assert await page.locator('#message').evaluate("e=>getComputedStyle(e).outlineStyle")=='none'
   assert await page.locator('#message').evaluate('e=>e.selectionEnd===e.value.length')
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

