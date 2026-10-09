"""Input normalization and action safety. Conversation routing lives in the graph."""
import re
from pydantic import BaseModel, ConfigDict
from typing import Literal
from .project import FEATURES
USAGE={'requests':0,'input_tokens':0,'output_tokens':0}
class Plan(BaseModel):
    model_config=ConfigDict(extra='forbid')
    feature: Literal[tuple(FEATURES)+('unknown',)]
    demo:bool
async def warm_up():pass

DEVANAGARI={w:r for r,words in {
    'lead':'लीड','leads':'लीड्स','status':'स्टेटस','stage':'स्टेज','note':'नोट','notes':'नोट्स नोटस','meeting':'मीटिंग',
    'site':'साइट','visit':'विज़िट विजिट','whatsapp':'व्हाट्सएप व्हाट्सऐप वॉट्सऐप वॉट्सएप','email':'ईमेल','mail':'मेल',
    'project':'प्रोजेक्ट','projects':'प्रोजेक्ट्स','task':'टास्क','tasks':'टास्क्स','property':'प्रॉपर्टी प्रोपर्टी',
    'properties':'प्रॉपर्टीज','dashboard':'डैशबोर्ड','history':'हिस्ट्री','document':'डॉक्यूमेंट','documents':'डॉक्यूमेंट्स',
    'source':'सोर्स','filter':'फ़िल्टर फिल्टर','search':'सर्च','bulk':'बल्क','upload':'अपलोड','sms':'एसएमएस','call':'कॉल',
    'assign':'असाइन','reassign':'रीअसाइन','schedule':'शेड्यूल','add':'ऐड एड','naya':'नया','nayi':'नई','banao':'बनाओ बनाएं',
    'banana':'बनाना','jodo':'जोड़ें जोड़ो','jodna':'जोड़ना','badle':'बदलें बदले','badalna':'बदलना','badlo':'बदलो',
    'change':'चेंज','update':'अपडेट','dikhao':'दिखाओ दिखाइए दिखाएं','dikha':'दिखा','kholo':'खोलो','kaise':'कैसे',
    'kaha':'कहाँ कहां','kya':'क्या','ka':'का','ki':'की','ke':'के','ko':'को','me':'में मे','hai':'है','hain':'हैं',
    'kare':'करें करे','karo':'करो','karna':'करना','mujhe':'मुझे','mere':'मेरे','mera':'मेरा','sirf':'सिर्फ','batao':'बताओ',
    'mat':'मत','contact':'संपर्क','namaste':'नमस्ते','namaskar':'नमस्कार','hello':'हेलो हैलो','hi':'हाय',
    'dhanyavaad':'धन्यवाद','shukriya':'शुक्रिया','thank':'थैंक','you':'यू',
}.items() for w in words.split()}

def romanize(text: str) -> str:
    text=re.sub(r'\bsite\s*vis(?:it[e]?|te)\b','site visit',text,flags=re.I)
    return re.sub(r'[ऀ-ॣ०-ॿ]+',lambda m:DEVANAGARI.get(m.group(0),m.group(0)),text.replace('।',' '))

WRITE_VERBS=(r"delete|remove|erase|archive|restore|export|download|send|forward|share|save|submit|update|edit|modify|overwrite|"
    r"upload|import|assign|reassign|transfer|merge|approve|publish|sync|call|dial|mark|deactivate|"
    r"bhej\w*|mita\w*|hata\w*|save\s+kar\w*|delete\s+kar\w*|update\s+kar\w*|badal\s+do|kar\s+do|kardo")
QUESTION_WORDS=re.compile(r"\b(how|why|what|where|when|which|can i|could i|is it possible|kaise|kya|kyu|kyun|kaha|kahan|batao|explain|show me how)\b|\?\s*$",re.I)

def write_request(message: str) -> bool:
    """A command to change, send or extract CRM data (not a question about how it works).

    The demo is read-only: such commands are refused before any browser action, whatever the planner says.
    """
    text=romanize(message).lower()
    verb=r"\b("+WRITE_VERBS+r")\b"
    if not re.search(verb,text):return False
    # "show export" / "open the edit form" asks to see a screen; "show leads and delete them" is still a command.
    if re.match(r"\s*(please\s+)?(show|open|demo|dikhao|dikha|kholo)\b",text) and not re.search(r"\b(and|then|aur|phir)\b.*"+verb,text):return False
    return not QUESTION_WORDS.search(text)

def declined(message: str) -> bool:
    message=romanize(message)
    return bool(re.search(r"\b(?:do not|don't|dont|never)\s+(?:contact|call|email|follow[ -]?up)|\bno\s+(?:follow[ -]?up|further contact)|\bstop contacting|\bnot interested\b|\bcontact mat",message,re.I))
