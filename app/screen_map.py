"""A map of every CRM page and the sections on it, read from the CRM's own source code.

Nothing here names a module, page or section. Routes come from the Angular routing modules,
labels from the sidebar definition and the English translation file, and section headings from
each routed component's template (and the templates of components it embeds). Rebuild after the
CRM changes:  python -m app.screen_map "C:\\LeadRat CRM\\QA Env\\Leadrat-Black-Web"
"""
import json
import re
import sys
from pathlib import Path

OUT=Path(__file__).resolve().parents[1]/'knowledge'/'screens.json'

def matching(text,start,open_char,close_char):
    """Index just past the bracket that closes text[start] (which must be open_char)."""
    depth=0;i=start;quote=None
    while i<len(text):
        c=text[i]
        if quote:
            if c=='\\':i+=2;continue
            if c==quote:quote=None
        elif c in '\'"`':quote=c
        elif c==open_char:depth+=1
        elif c==close_char:
            depth-=1
            if depth==0:return i+1
        i+=1
    return len(text)

def objects(array_text):
    """Top-level {...} literals inside an array literal's text."""
    found=[];i=0
    while True:
        i=array_text.find('{',i)
        if i<0:return found
        end=matching(array_text,i,'{','}');found.append(array_text[i:end]);i=end

def own_fields(obj):
    """The object's text without nested arrays/objects, so a child's path is not read as its parent's."""
    body=obj[1:-1];out=[];i=0
    while i<len(body):
        c=body[i]
        if c in '[{':
            i=matching(body,i,c,']' if c=='[' else '}');out.append(' ');continue
        out.append(c);i+=1
    return ''.join(out)

def string_field(text,name):
    m=re.search(r'\b'+name+r"\s*:\s*['\"`]([^'\"`]*)['\"`]",text)
    return m.group(1) if m else None

def array_field(obj,name):
    m=re.search(r'\b'+name+r'\s*:\s*\[',obj)
    return obj[m.end()-1:matching(obj,m.end()-1,'[',']')] if m else None

class Source:
    def __init__(self,root):
        self.root=Path(root);self.app=self.root/'src'/'app'
        self.files={p:p.read_text('utf8',errors='ignore') for p in self.app.rglob('*.ts') if not p.name.endswith('.spec.ts')}
        self.classes={}
        for path,text in self.files.items():
            for name in re.findall(r'export\s+class\s+(\w+)',text):self.classes[name]=path
        self.templates={};self.selectors={}
        for path,text in self.files.items():
            for m in re.finditer(r'@Component\(\{(.*?)\}\)\s*export\s+class\s+(\w+)',text,re.S):
                url=string_field(m.group(1),'templateUrl');selector=string_field(m.group(1),'selector')
                if url:
                    template=(path.parent/url).resolve()
                    self.templates[m.group(2)]=template
                    if selector:self.selectors[selector]=template
        i18n=self.root/'src'/'assets'/'i18n'/'en.json'
        self.english=json.loads(i18n.read_text('utf8')) if i18n.is_file() else {}

    def translate(self,key):
        value=self.english
        for part in key.split('.'):
            value=value.get(part) if isinstance(value,dict) else None
        return value if isinstance(value,str) else None

    def imports(self,path):
        """name -> file for this file's imports from the application (not from libraries)."""
        found={}
        for names,target in re.findall(r"import\s*\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]",self.files.get(path,'')):
            if target.startswith('src/'):file=self.root/(target+'.ts')
            elif target.startswith('.'):file=(path.parent/(target+'.ts')).resolve()
            else:continue
            file=next((f for f in self.files if f.resolve()==file.resolve()),None) if file not in self.files else file
            if file:
                for name in names.split(','):
                    name=name.split(' as ')[-1].strip()
                    if name:found[name]=file
        return found

    def array(self,path,name,depth=0):
        """The objects of the array literal bound to name, following an import if it is declared elsewhere."""
        text=self.files.get(path,'')
        decl=re.search(r'\b(?:const|let|var)\s+'+name+r'\s*(?::\s*[\w<>\[\]]+\s*)?=\s*\[',text)
        if decl:
            start=decl.end()-1
            return objects(text[start:matching(text,start,'[',']')])
        target=self.imports(path).get(name)
        return self.array(target,name,depth+1) if target and depth<3 else []

    def routes_of(self,path,depth=0,seen=None):
        """Every route a module registers: its own RouterModule calls plus those of the modules it imports."""
        seen=seen if seen is not None else set()
        if path in seen or depth>3:return []
        seen.add(path);text=self.files.get(path,'');found=[]
        for call in re.finditer(r'RouterModule\.for(?:Root|Child)\(\s*(\w+|\[)',text):
            if call.group(1)=='[':found+=objects(text[call.end()-1:matching(text,call.end()-1,'[',']')])
            else:found+=self.array(path,call.group(1))
        imported=self.imports(path)
        block=re.search(r'\bimports\s*:\s*\[',text)
        # An NgModule follows what its imports list names; a file of shared constants (an imports list
        # spread into a module) follows every name its body uses.
        body=text[block.end()-1:matching(text,block.end()-1,'[',']')] if block else re.sub(r'import\s*\{[^}]*\}\s*from[^;]+;','',text)
        used=set(re.findall(r'\w+',body))
        for name,target in imported.items():
            if name in used and target!=path:
                found+=self.routes_of(target,depth+1,seen)
        return found

    def walk(self,file,prefix,seen,routes=None):
        """(full path, component) for each route, following children and lazily loaded modules."""
        for obj in self.routes_of(file) if routes is None else routes:
            fields=own_fields(obj)
            path=string_field(fields,'path')
            if path is None or path=='**' or string_field(fields,'redirectTo') is not None:continue
            if re.search(r'canActivate\s*:\s*\[[^\]]*NoAuthGuard',obj):continue  # pages for signed-out visitors (sign-in, password reset)
            full='/'.join(p for p in (prefix,path) if p)
            component=re.search(r'\bcomponent\s*:\s*(\w+)',fields)
            if component:yield full,component.group(1)
            children=array_field(obj,'children')
            if children:yield from self.walk(file,full,seen,objects(children))
            lazy=re.search(r"loadChildren\s*:\s*\(\)\s*=>\s*import\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\.then\(\s*\(?\s*\w+\s*\)?\s*=>\s*\w+\.(\w+)",fields)
            if lazy:
                target=self.classes.get(lazy.group(2))
                if target and (target,full) not in seen:
                    seen.add((target,full));yield from self.walk(target,full,seen)

    def sidebar(self):
        """Route -> label for every sidebar entry and its sub-entries, as the CRM renders them."""
        labels={}
        for path,text in self.files.items():
            if 'navItems' not in text or 'labelKey' not in text:continue
            for m in re.finditer(r'\{[^{}]*\b(?:route|clickRoute)\s*:[^{}]*\}',text):
                item=m.group(0)
                label=self.translate(string_field(item,'labelKey') or '') or string_field(item,'label')
                if not label:continue
                for key in ('route','clickRoute'):
                    route=string_field(item,key)
                    if route:labels.setdefault(route.strip('/'),label)
        return labels

    def texts(self,template,depth=0,seen=None):
        """(kind, text) for static text in a template and in the templates of components it embeds."""
        seen=seen or set()
        if template in seen or not template.is_file():return []
        seen.add(template);html=template.read_text('utf8',errors='ignore')
        html=re.sub(r'<!--.*?-->','',html,flags=re.S)
        def resolve(fragment):
            fragment=re.sub(r"\{\{\s*['\"]([\w.-]+)['\"]\s*\|\s*translate\s*\}\}",lambda m:self.translate(m.group(1)) or '',fragment)
            if '{{' in fragment:fragment=re.sub(r'\{\{.*?\}\}','',fragment)
            return ' '.join(re.sub(r'<[^>]+>',' ',fragment).split())
        found=[]
        for m in re.finditer(r'<(h[1-6])\b[^>]*>(.*?)</\1>',html,re.S):
            text=resolve(m.group(2))
            if is_title(text):found.append(('heading',text))
        for m in re.finditer(r'<(\w[\w-]*)\b([^>]*\bclass="[^"]*\b(?:fw-(?:600|700|semi-bold|bold)|header-\d)\b[^"]*"[^>]*)>([^<]*(?:<(?!/?\1\b)[^<]*)*?)</\1>',html,re.S):
            text=resolve(m.group(3))
            if is_title(text):found.append(('heading',text))
        for m in re.finditer(r'>([^<>]+)<',html):
            text=resolve(m.group(1))
            if 2<=len(text)<=60 and re.search(r'[A-Za-z]',text):found.append(('text',text))
        if depth<2:
            for tag in set(re.findall(r'<([a-z][\w]*-[\w-]+)\b',html)):
                child=self.selectors.get(tag)
                if child:found+=[('text',t) for _,t in self.texts(child,depth+1,seen)]
        return found

def is_title(text):
    """A section title rather than a message: short, and not a sentence, question or exclamation."""
    return 2<=len(text)<=60 and len(text.split())<=7 and not text.rstrip().endswith(('!','?','.',':'))

def links(src,paths,labels):
    """Pages the CRM links to (sidebar, routerLink, router.navigate, path constants) and the human text
    of any object that names a page's path, such as a settings card's label and description."""
    linked={p for p in paths if p in labels};extra={p:[] for p in paths}
    by_segment={}
    for path in paths:by_segment.setdefault(path.split('/')[-1],[]).append(path)
    files=list(src.files.items())+[(f,f.read_text('utf8',errors='ignore')) for f in src.app.rglob('*.html')]
    for file,text in files:
        if 'RouterModule.for' in text:continue
        code=re.sub(r'/\*.*?\*/','',re.sub(r'^\s*//.*$','',text,flags=re.M),flags=re.S)
        code=re.sub(r'<!--.*?-->','',code,flags=re.S)
        def resolve(literal):
            literal=literal.strip('/')
            if literal in extra:return literal
            match=by_segment.get(literal) if '/' not in literal else None
            return match[0] if match and len(match)==1 else None
        for nav in re.findall(r'navigate(?:ByUrl)?\(\s*\[([^\]]*)\]',code):
            page=resolve('/'.join(re.findall(r"['\"]([^'\"]+)['\"]",nav)))
            if page:linked.add(page)
        for literal in re.findall(r"['\"`](/?[\w-]+(?:/[\w-]+)*)['\"`]",code):
            page=resolve(literal)
            if page and (('/' in literal.strip('/')) or 'routerLink' in code):linked.add(page)
        for obj in re.finditer(r"\{[^{}]*?['\"]/?([\w-]+/[\w-]+(?:/[\w-]+)*)['\"][^{}]*\}",code):
            page=obj.group(1).strip('/')
            if page not in extra:continue
            for value in re.findall(r":\s*['\"]([^'\"]{2,80})['\"]",obj.group(0)):
                value=src.translate(value) or value if re.fullmatch(r'[A-Z_]+\.[\w.-]+',value) else value
                if value.strip('/')!=page and (' ' in value or any(c.isupper() for c in value)) and not re.fullmatch(r'[A-Z_]+\.[\w.-]+',value):
                    extra[page].append(value)
    return linked,extra

def humanise(segment):
    return ' '.join(w.capitalize() for w in re.split(r'[-_]',segment) if w)

def build(root):
    src=Source(root)
    labels=src.sidebar()
    pages={}
    for path,component in src.walk(src.app/'app-routing.module.ts','',set()):
        if ':' in path or not path or path in pages:continue
        # The full trail keeps pages apart that share a sidebar label (e.g. a "Status" report for leads and for data).
        segments=path.split('/')
        trail=[labels.get('/'.join(segments[:i+1])) or humanise(s) for i,s in enumerate(segments)]
        trail=[t for i,t in enumerate(trail) if i==0 or t!=trail[i-1]]
        name=' › '.join(trail)
        texts=src.texts(src.templates.get(component,Path('-')))
        headings=list(dict.fromkeys(t for k,t in texts if k=='heading'))
        words=list(dict.fromkeys(t for _,t in texts))
        pages[path]={'path':'/'+path,'name':name,'headings':headings[:40],'context':words[:60]}
    linked,extra=links(src,set(pages),labels)
    entries=[]
    for key,page in pages.items():
        described=list(dict.fromkeys(extra[key]))
        common={'path':page['path'],'page':page['name'],'reachable':key in linked}
        entries.append({'id':'p'+str(len(entries)),**common,'section':None,
                        'text':page['name']+': '+', '.join(described+page['context'][:40])})
        for heading in page['headings']:
            if heading.casefold()==page['name'].split(' › ')[-1].casefold():continue
            entries.append({'id':'p'+str(len(entries)),**common,'section':heading,'text':page['name']+' › '+heading})
    return {'source':'Angular routes, sidebar and templates of the CRM web client','pages':len(pages),'entries':entries}

if __name__=='__main__':
    result=build(sys.argv[1])
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=0)+'\n','utf8')
    print(f"{result['pages']} pages, {len(result['entries'])} locations -> {OUT}")
