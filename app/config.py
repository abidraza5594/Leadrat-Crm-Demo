import os
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
CRM_URL = os.getenv('CRM_URL', 'http://localhost:4200').rstrip('/')
CRM_ORIGIN = '{0.scheme}://{0.netloc}'.format(urlsplit(CRM_URL))
SANDBOX_CONFIRMED = os.getenv('SANDBOX_CONFIRMED', 'false').lower() == 'true'
ORIGINS = set(os.getenv('BEACON_ORIGINS', 'http://localhost:8010,http://localhost:8011,http://127.0.0.1:8010,http://127.0.0.1:8011').split(','))
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
MODEL = os.getenv('OLLAMA_MODEL', 'ministral-3:3b')
NUM_GPU = int(os.getenv('OLLAMA_NUM_GPU', '0'))
# The demo browser is hidden by default; visitors see it only inside the website popup.
HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'
LOCAL_DEVICE_LOCATION = os.getenv('LOCAL_DEVICE_LOCATION', 'false').lower() == 'true'
# Saved CRM login (cookies + localStorage) reused by each new hidden browser. Contains auth tokens; never commit it.
BROWSER_STATE = Path(os.getenv('BEACON_BROWSER_STATE', ROOT / '.browser' / 'crm-state.json'))
TTS_URL = os.getenv('TTS_URL', '').rstrip('/')
TTS_VOICE = os.getenv('TTS_VOICE', 'af_heart')
TTS_PROVIDER = os.getenv('TTS_PROVIDER','local' if TTS_URL else 'browser')
PROVIDER = os.getenv('PLANNER_PROVIDER','ollama')
OPENAI_MODEL = os.getenv('OPENAI_MODEL','gpt-6-luna')
LOCAL_MODEL_URL = os.getenv('LOCAL_MODEL_URL', 'http://127.0.0.1:8012').rstrip('/')
LOCAL_CHAT_MODEL = os.getenv('LOCAL_CHAT_MODEL', 'qwen2.5-1.5b-instruct')
