"""Generate the demo-video voiceover with the Soniox cloned voice from ai-video-plugin.

Uses the plugin's own Soniox generator and its .env (SONIOX_API_KEY, SONIOX_VOICE_ID).
Output: docs/demo-video/narration/scene_XX.wav
    python docs/demo-video/make_narration.py
"""
import json
import shutil
import sys
from pathlib import Path

PLUGIN = Path(r'C:\ABID\YOUTUBE AUTO\ai-video-plugin')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PLUGIN))

from dotenv import dotenv_values  # noqa: E402
from modules.soniox_generation import generate  # noqa: E402

env = dotenv_values(PLUGIN / '.env')
voice = env.get('SONIOX_VOICE_ID')
if not voice:
    sys.exit('SONIOX_VOICE_ID is missing from the plugin .env')

scenes = json.loads((HERE / 'narration.json').read_text(encoding='utf-8'))['scenes']
requests = [{'scene_id': s['id'], 'model': 'tts-rt-v2', 'voice': voice, 'language': 'hi',
             'audio_format': 'wav', 'sample_rate': 48000, 'speed': 1.06, 'text': s['text']}
            for s in scenes]
work = HERE / '.work'
for result in generate(requests, work, notify=lambda **k: print(k['message'])):
    print(result)
out = HERE / 'narration'
out.mkdir(exist_ok=True)
for s in scenes:
    shutil.copyfile(work / 'soniox' / s['id'] / 'audio.wav', out / f"{s['id']}.wav")
print('Narration saved to', out)
