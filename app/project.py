"""A project owns knowledge and tool descriptions; the conversation engine is generic."""
import json
import os
from pathlib import Path
from .config import ROOT
from .lead_guides import GUIDES

def load_project():
    path=Path(os.getenv('BEACON_PROJECT_FILE',ROOT/'knowledge/project.json'))
    project=json.loads(path.read_text('utf8'))
    project['knowledge_dir']=str((path.parent/project.get('docs_dir','docs')).resolve())
    features={f['id']:f for f in json.loads((path.parent/project['features_file']).read_text('utf8'))}
    if project.get('adapter')=='leadrat':features.update(GUIDES)
    for key,f in features.items():
        f['workspace']=key in project.get('workspace_features',[])
        f['knowledge_topics']=project['module_topics'][f['module']]
        f['description']=project.get('descriptions',{}).get(key,f['title']+': '+f['facts'][0])[:145]
        f['intent_description']=project.get('descriptions',{}).get(key,f['title'])
    return project,features

PROJECT,FEATURES=load_project()
