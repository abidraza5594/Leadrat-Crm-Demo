"""Produce manager-facing rows without discarding any paired test answer."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/beacon-training-v4/comparison'
def read(p):return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
preview='--preview' in sys.argv
old=read(ROOT/'outputs/beacon-training-v3/evaluation/predictions.jsonl')+([] if preview else read(OUT/'old.jsonl'))
new=read(OUT/('new-smoke.jsonl' if preview else 'new.jsonl'))
if not preview:
 assert len(old)==len(new)==293
 assert len({r['id'] for r in new})==293
 assert sum(r['dataset']=='regression' for r in new)==233
 assert sum(r['dataset']=='fresh' for r in new)==60
 assert all(r['weights_sha256']=='f1d618ed1152e2cb8443bda4e3316e6f5a704c4cb3fa6e8160bbf5e3afc1d99f' for r in new)
 assert all(r['weights_sha256']=='e23139ba1b61a4912f476120cef8ff6edb8a8a726a0d8c9a9537308cc492ffe3' for r in old[233:])
before={r['id']:r for r in old};assert len(before)==len(old)
TOPICS=['Job role','Seniority','Company name','Business type','Number of agents','Customer problems','Tools currently used','Current working process','Cities','Countries','Monthly leads: minimum','Monthly leads: maximum','Lead sources','Purchase decision authority','Next-step timing','Permission for sales contact','Contact name','Email','Phone','Lead score','Possible score range','Follow-up decision']
ENGLISH={'unknown':'Not stated','brokerage':'Brokerage','developer':'Developer','channel_partner':'Channel partner','other_real_estate':'Other real estate business','unrelated':'Not a real estate business','owner':'Owner','executive':'Executive','manager':'Manager','individual_contributor':'Individual contributor','manual':'Manual process','unsatisfied_crm':'Unhappy with current CRM','satisfied_crm':'Happy with current CRM','approver':'Can approve the purchase','sponsored_evaluator':'Evaluating with decision-maker support','none':'No purchase authority','within_30_days':'Within 30 days','later':'Later than 30 days','declined':'Declined follow-up','sales_handoff':'Refer to sales','human_review':'Review missing details first','nurture':'Follow up later if permitted','graceful_close':'Close without sales follow-up'}
def value(x,field):
 if x is None:return 'Not enough information' if field in ('icp_score','score_range') else 'Not stated'
 if isinstance(x,bool):return 'Yes' if x else 'No'
 if isinstance(x,list):return ' to '.join(map(str,x)) if field=='score_range' else '\n'.join(map(str,x)) if x else 'None stated by customer'
 return ENGLISH.get(x,str(x)) if isinstance(x,str) else x
details=[];cases=[];turns=[]
ordered=sorted(new,key=lambda r:(r['dataset']!='regression',r['id']))
for number,after in enumerate(ordered,1):
 prior=before[after['id']];assert prior['gold']==after['gold'] and prior['transcript']==after['transcript']
 assert len(prior['checks'])==len(after['checks'])==22
 case=f'C{number:03}';group='Original 233' if after['dataset']=='regression' else 'New examples'
 for t in after['transcript']:turns.append([case,after['id'],t['turn_id'],'Customer' if t['speaker']=='visitor' else 'Beacon',t['text']])
 for i,(a,b) in enumerate(zip(prior['checks'],after['checks'])):
  assert a['field']==b['field'] and a['expected']==b['expected']
  change='Improved' if not a['correct'] and b['correct'] else 'Needs attention' if a['correct'] and not b['correct'] else 'Still matches' if b['correct'] else 'Still needs review'
  note='Both versions match the expected answer.' if a['correct'] and b['correct'] else 'The latest answer matches; the previous answer did not.' if b['correct'] else 'The previous answer matched; the latest answer needs review.' if a['correct'] else 'Both answers differ from the expected answer.'
  if not after['valid']:note='Latest complete answer was unusable. No valid details could be read.'
  elif not b['correct'] and b['method']=='Normalized text/set equality':note+=' Different wording can have the same meaning; check the conversation.'
  details.append([case,group,TOPICS[i],value(b['expected'],b['field']),value(a['actual'],a['field']) if prior['valid'] else 'Unusable answer',value(b['actual'],b['field']) if after['valid'] else 'Unusable answer','Match' if a['correct'] else 'Review','Match' if b['correct'] else 'Review',change,note,'Yes' if b['reference_known'] else 'No'])
 cases.append([case,group,prior['matched_fields'],after['matched_fields'],22,'Usable' if prior['valid'] else 'Unusable','Usable' if after['valid'] else 'Unusable',value(after['gold']['route'],'route'),value(prior['pred']['route'],'route') if prior['pred'] else 'Unusable',value(after['pred']['route'],'route') if after['pred'] else 'Unusable',prior['routing_correct'],after['routing_correct'],prior['unsafe_handoff'],after['unsafe_handoff']])
reg=[(before[r['id']],r) for r in ordered if r['dataset']=='regression']
oldmatch=sum(a['matched_fields'] for a,b in reg);newmatch=sum(b['matched_fields'] for a,b in reg)
stats={'old_matches':oldmatch,'new_matches':newmatch,'total_details':233*22,'old_wrong_sales':sum(a['unsafe_handoff'] for a,b in reg),'new_wrong_sales':sum(b['unsafe_handoff'] for a,b in reg),'improved_details':sum(r[8]=='Improved' for r in details if r[1]=='Original 233'),'worse_details':sum(r[8]=='Needs attention' for r in details if r[1]=='Original 233')}
topic_changes=[]
for i,name in enumerate(TOPICS):
 a=sum(x['checks'][i]['correct'] for x,y in reg);b=sum(y['checks'][i]['correct'] for x,y in reg)
 topic_changes.append({'topic':name,'before':a,'after':b,'change':b-a})
stats['topics']=topic_changes
stats['groups']={}
for group_name in ('regression','fresh'):
 paired=[(before[r['id']],r) for r in ordered if r['dataset']==group_name]
 if paired:
  stats['groups'][group_name]={'conversations':len(paired),'details_checked':len(paired)*22}
  for side,index in [('before',0),('after',1)]:
   rows=[p[index] for p in paired]
   stats['groups'][group_name][side]={key:sum(r[key] for r in rows) for key in ('matched_fields','valid','fully_matched','routing_correct','unsafe_handoff')}
best=sorted(topic_changes,key=lambda r:r['change'],reverse=True)[:3]
worst=sorted(topic_changes,key=lambda r:r['change'])[:3]
notes=[f"Of 5,126 original detail checks, {stats['improved_details']} improved and {stats['worse_details']} stopped matching.",
 'Higher match percentages are better. Fewer unusable answers and wrong sales referrals are better.',
 'This adapter reads customer details. It does not generate the website\'s general CRM explanations.',
 'The original 233 conversations informed improvement work. They are comparison tests, not new customer evidence.',
 '60 additional prepared examples cover 30 scenarios. Their patterns are related to the training examples.',
 'A match is a reference-value comparison. Different valid wording can fail, especially customer problems.',
 'Lead scores describe business fit. They are not confidence that the model is correct.',
 'Review incorrect referrals and new mistakes before enabling automatic customer follow-up.',
 'Hugging Face contains the new version. The live website has not been switched to it.']
notes.insert(1,'Largest gains: '+', '.join(f"{r['topic']} ({r['change']:+} matches)" for r in best if r['change']>0)+'.' if any(r['change']>0 for r in best) else 'No answer category gained reference matches.')
notes.insert(2,'Areas that worsened: '+', '.join(f"{r['topic']} ({r['change']} matches)" for r in worst if r['change']<0)+'.' if any(r['change']<0 for r in worst) else 'No answer category lost reference matches.')
notes.insert(3,'Recommendation: supervised demo only; incorrect sales referrals remain, so do not enable automatic follow-up based on this model alone.' if any(r['unsafe_handoff'] for r in new) else 'Recommendation: complete live application tests before release; these prepared examples do not prove real-customer reliability.')
training=[['Training record','Before: 30 Sep','After: 1 Oct'],['Examples in latest training round',2811,10611],['Additional controlled examples','Not applicable',7800],['Additional training passes',2,1],['Continuation from prior model','Yes','Yes'],['Comparison conversations',233,233],['Additional examples compared',60,60],['Published version','v3','v4'],['Publication verified','Yes','Yes']]
result={'details':details,'cases':cases,'turns':turns,'topics':TOPICS,'notes':notes,'training':training,'stats':stats}
(OUT/('report-data-preview.json' if preview else 'report-data.json')).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
if not preview:(OUT/'comparison-summary.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
print(json.dumps(stats,indent=2))
