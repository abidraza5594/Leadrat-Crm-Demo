"""Search product meaning within the SAME topic as the selected capability."""
import asyncio
import hashlib
import json
import os
from . import docs
from .handbook_faq import lookup

MODEL='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
REVISION='e8f8c211226b894fcb81acc59f3b34ba3efd5f42'

class SemanticKnowledge:
    def __init__(self,store=None,project='leadrat',directory=None):
        self.store=store;self.project=project;self.model=None;self.documents=[];self.vectors=None;self.version=''
        self.ready=False;self.error=None;self.lock=asyncio.Lock()
        self.directory=directory

    async def warm(self):
        async with self.lock:
            if self.ready:return
            try:
                def load():
                    from .embeddings import Encoder
                    self.model=Encoder()
                await asyncio.to_thread(load)
                documents=await asyncio.to_thread(docs.load,self.directory)
                self.version=hashlib.sha256((MODEL+REVISION+'onnx-quint8-avx2'+json.dumps(documents,sort_keys=True)).encode()).hexdigest()
                cached=await self.store.knowledge(self.project,self.version) if self.store else []
                import numpy as np
                if len(cached)==len(documents) and cached:
                    self.documents=[d for d,_ in cached];self.vectors=np.array([v for _,v in cached])
                else:
                    self.documents=documents
                    self.vectors=await asyncio.to_thread(self.model.encode,
                        [d['module']+' '+d['section']+' '+d['text'] for d in documents],normalize_embeddings=True,show_progress_bar=False)
                    if self.store:await self.store.put_knowledge(self.project,self.version,[(d,v.tolist()) for d,v in zip(documents,self.vectors)])
                self.ready=True;self.error=None
            except Exception as exc:self.error=type(exc).__name__;raise

    async def retrieve(self,question,topic):
        if not self.ready:return []
        query=await asyncio.to_thread(self.model.encode,question,normalize_embeddings=True,show_progress_bar=False)
        if self.store:
            result=await self.store.nearest(self.project,self.version,query.tolist(),topic)
            if result is not None:return result
        scores=self.vectors@query
        return sorted([(float(s),d) for s,d in zip(scores,self.documents) if d['module']==topic],key=lambda x:x[0],reverse=True)[:4]

    def topic_description(self,topic):
        purpose=next((d for d in self.documents if d['module']==topic and 'Purpose' in d['section']),None)
        return purpose['text'][:130] if purpose else topic

    async def answer(self,question,decision,features):
        reviewed=lookup(question) if self.project=='leadrat' else None
        if reviewed and reviewed['module']==decision.topic:
            return {'text':reviewed['answer'],'grounded':True,'sources':[docs.cite(reviewed)],'mode':'reviewed_topic_answer'}
        evidence=await self.retrieve(question,decision.topic)
        # Approved tool facts describe exactly the selected demo. A vector hit
        # cannot replace those with a superficially related module's answer.
        if decision.feature in features:
            feature=features[decision.feature]
            text=' '.join(feature['facts']) if not decision.demo else feature['facts'][0]
            return {'text':text,'grounded':True,'sources':[feature['source']],
                'evidence':[d['id'] for _,d in evidence],'mode':'capability_grounded'}
        if evidence and evidence[0][0]>=0.50:
            best=evidence[0][1]
            return {'text':docs.extractive(question,best),'grounded':True,'sources':[docs.cite(best)],'mode':'topic_retrieval'}
        return {'text':'I do not have a verified answer or walkthrough for that request. Could you tell me which product feature you mean?',
            'grounded':False,'sources':[],'mode':'clarification'}
