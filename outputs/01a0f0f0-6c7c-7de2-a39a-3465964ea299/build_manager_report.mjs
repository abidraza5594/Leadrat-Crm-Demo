import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const dir=path.dirname(fileURLToPath(import.meta.url));
const root='C:/Leadrat AI/Beacon';
const rows=(await fs.readFile(root+'/outputs/beacon-training-v3/evaluation/predictions.jsonl','utf8')).trim().split('\n').map(JSON.parse);
const replay=JSON.parse(await fs.readFile(path.join(dir,'answer_recheck.json'),'utf8'));
const replayMap=new Map(replay.cases.map(x=>[x.id,x]));
rows.sort((a,b)=>(b.unsafe_handoff-a.unsafe_handoff)||(a.valid-b.valid)||(a.matched_fields-b.matched_fields)||a.id.localeCompare(b.id));
const names={role:'Job role',seniority:'Position level','organisation.name':'Company name','organisation.type':'Business type','organisation.agents':'Team size',pain_points:'Problems reported',current_tooling:'Tools used',process:'Working process','geography.cities':'Cities','geography.countries':'Countries','monthly_leads.min':'Monthly leads: minimum','monthly_leads.max':'Monthly leads: maximum',lead_sources:'Lead sources',influence:'Purchase authority',next_step:'Next step and timing',consent:'Permission to contact','contact.name':'Contact name','contact.email':'Email address','contact.phone':'Phone number',icp_score:'Lead suitability score',score_range:'Possible score range',route:'Recommended follow-up'};
const words={unknown:'Not known',brokerage:'Property brokerage',developer:'Property developer',channel_partner:'Channel partner',other_real_estate:'Other real estate business',unrelated:'Not a real estate buyer',owner:'Owner',executive:'Executive',manager:'Manager',individual_contributor:'Individual employee',manual:'Manual work',unsatisfied_crm:'Unhappy with current customer management tool',satisfied_crm:'Satisfied with current customer management tool',approver:'Can approve the purchase',sponsored_evaluator:'Evaluating for a decision-maker',none:'No purchase authority',within_30_days:'Within 30 days',later:'Later than 30 days',declined:'Not interested',sales_handoff:'Send to sales',human_review:'Ask a person to review',nurture:'Keep in touch',graceful_close:'Close politely'};
const textFields=new Set(['role','organisation.name','pain_points','current_tooling','geography.cities','geography.countries','lead_sources','contact.name','contact.email','contact.phone']);
function value(v,field){if(v===undefined)return 'No answer provided';if(v===null)return 'Not known';if(typeof v==='boolean')return v?'Yes':'No';if(Array.isArray(v))return v.length?(field==='score_range'?v.join(' to '):v.join('; ')):'None stated';return words[v]??v;}
function rawValue(r,f){let x;try{x=JSON.parse(r.raw);}catch{return undefined;}for(const k of f.split('.'))x=x?.[k];return x;}
function result(r,c){if(!r.valid)return 'Unusable answer';if(c.correct)return 'Correct';if(c.actual===null||c.actual==='unknown')return 'Missing answer';if(c.expected===null||c.expected==='unknown')return 'Unsupported answer';if(textFields.has(c.field))return 'Needs wording review';return 'Incorrect';}
function reason(r,c){let s=result(r,c);if(s==='Correct')return c.expected===null||c.expected==='unknown'?'Correctly leaves this detail unknown.':'Matches the expected answer.';
 if(s==='Unusable answer')return r.parse_reason==='evidence_not_visitor'?'The answer relied on a Beacon message instead of the visitor. The complete answer was rejected.':'The complete answer contains an unsupported position level and was rejected.';
 if(s==='Needs wording review')return 'The wording or listed details differ from the expected answer. Read the visitor statement to decide whether the meaning is equivalent.';
 if(s==='Missing answer')return 'The expected detail is available, but the model left it unknown.';
 if(s==='Unsupported answer')return 'The model supplied a detail that the expected answer leaves unknown.';
 if(c.field==='route')return 'The proposed follow-up differs from the expected decision.';
 if(c.field==='icp_score'||c.field==='score_range')return 'The lead score differs from the expected calculation.';
 if(c.field==='consent')return 'The model did not correctly record permission to contact.';
 return 'The model value differs from the expected answer.';}
function support(r,c){const ids=new Set();for(const ev of [r.gold.evidence,r.pred?.evidence??{}])for(const [key,tids] of Object.entries(ev))if(c.field===key||c.field.startsWith(key+'.')||key.startsWith(c.field+'.'))for(const id of tids)ids.add(id);return ids;}
function context(r,c){if(['icp_score','score_range','route'].includes(c.field))return ['Based on the whole conversation','See all questions and visitor answers for this conversation.'];const ids=support(r,c),q=[],v=[];for(let i=0;i<r.transcript.length;i++){let t=r.transcript[i];if(t.speaker==='visitor'&&ids.has(t.turn_id)){v.push(t.text);let before=r.transcript.slice(0,i).reverse().find(x=>x.speaker==='beacon');if(before&&!q.includes(before.text))q.push(before.text);}}return [q.join('\n')||'No specific question linked to this detail',v.join('\n')||'No visitor statement linked to this detail. See the full conversation.'];}
const details=rows.flatMap(r=>r.checks.map(c=>[r.id,names[c.field],...context(r,c),value(c.expected,c.field),value(r.valid?c.actual:rawValue(r,c.field),c.field),result(r,c),reason(r,c),c.reference_known?'Yes':'No']));
const conversations=rows.map(r=>{let p=replayMap.get(r.id);return [r.id,r.matched_fields,22,null,r.valid?'Usable':'Unusable',value(r.gold.route,'route'),value(rawValue(r,'route'),'route'),r.routing_correct?'Correct':'Incorrect',value(p.website_decision,'route'),p.correct?'Correct':'Incorrect',r.unsafe_handoff?'Yes':'No',p.wrong_sales?'Yes':'No',r.checks.filter(c=>!c.correct).map(c=>names[c.field]).join(', ')||'None'];});
const questions=[];
for(const r of rows){let pending=[],visitor=[],ids=[];function flush(){if(!pending.length&&!visitor.length)return;let cs=r.checks.filter(c=>![ 'icp_score','score_range','route'].includes(c.field)&&[...support(r,c)].some(id=>ids.includes(id)));questions.push([r.id,pending.join('\n')||'Visitor volunteered this information',visitor.join('\n')||'No visitor reply in the test conversation',cs.map(c=>names[c.field]+': '+value(r.valid?c.actual:rawValue(r,c.field),c.field)).join('\n')||'No finding directly linked to this exchange',cs.map(c=>names[c.field]+': '+value(c.expected,c.field)).join('\n')||'See Answer details for the full conversation assessment',cs.map(c=>names[c.field]+': '+result(r,c)).join('\n')||'Not separately scored']);pending=[];visitor=[];ids=[];}
 for(const t of r.transcript){if(t.speaker==='beacon'){if(visitor.length)flush();pending.push(t.text);}else{visitor.push(t.text);ids.push(t.turn_id);}}flush();
 const final=r.checks.filter(c=>['icp_score','score_range','route'].includes(c.field));
 questions.push([r.id,'Final assessment after the whole conversation','Based on all visitor answers above.',final.map(c=>names[c.field]+': '+value(r.valid?c.actual:rawValue(r,c.field),c.field)).join('\n'),final.map(c=>names[c.field]+': '+value(c.expected,c.field)).join('\n'),final.map(c=>names[c.field]+': '+result(r,c)).join('\n')]);}
const book=Workbook.create();const summary=book.worksheets.add('Summary');const qa=book.worksheets.add('Questions and answers');const det=book.worksheets.add('Answer details');const conv=book.worksheets.add('Conversation results');
const navy='#183A52',blue='#EAF2F7',red='#FBE6E5',green='#E3F2E9',amber='#FFF1D6';
function set(s,cell,data){s.getRange(cell).values=data;}
function base(s,end,widths,title,subtitle){s.showGridLines=false;s.getRangeByIndexes(0,0,end,widths.length).format={font:{name:'Arial',size:11,color:'#253746'},verticalAlignment:'top',rowHeight:24};widths.forEach((w,i)=>s.getRangeByIndexes(0,i,end,1).format.columnWidth=w);set(s,'A1',[[title]]);s.getRange('A1').format.font={name:'Arial',size:19,bold:true,color:navy};s.getRange('A1').format.rowHeight=34;set(s,'A2',[[subtitle]]);s.freezePanes.freezeRows(5);s.freezePanes.freezeColumns(1);}
function head(s,range){s.getRange(range).format={fill:navy,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:34,verticalAlignment:'center'};}
function table(s,data,headers,widths,title,subtitle,name){let end=data.length+5;const last=String.fromCharCode(64+headers.length);base(s,end,widths,title,subtitle);set(s,'A5',[headers]);set(s,'A6',data);head(s,`A5:${last}5`);s.getRange(`A6:${last}${end}`).format.wrapText=true;s.tables.add(`A5:${last}${end}`,true,name);data.forEach((r,i)=>{let lines=Math.max(...r.map((x,j)=>String(x??'').split('\n').reduce((n,t)=>n+Math.max(1,Math.ceil(t.length/Math.max(7,widths[j]-4))),0)));s.getRange(`A${i+6}:${last}${i+6}`).format.rowHeight=Math.min(409,Math.max(38,lines*15+12));});return end;}
const qe=table(qa,questions,['Conversation','Question asked by Beacon','Visitor answer','What the model understood','Expected understanding','Result for each detail'],[17,48,65,53,53,44],'Questions, visitor answers and model findings','Model findings are produced after the whole conversation. They are shown here in plain English.','QuestionAnswers');
set(qa,'A3',[['1,146 question-answer exchanges, followed by 233 final assessments. Cases needing attention appear first. Later corrections can change the final answer.']]);
set(qa,'A4',[['Source: completed model test, 30 September 2026. https://www.kaggle.com/code/abidrazaansari/beacon-v3-held-out-evaluation?scriptVersionId=354123767']]);
const de=table(det,details,['Conversation','Detail checked','Related question asked','Related visitor statement','Expected answer','Model answer','Result','Why this result','Expected detail available'],[17,28,47,65,43,43,25,60,17],'Every answer checked','Correct means the answer matches the prepared expected answer. Different wording is marked for review.','AnswerDetails');
set(det,'A3',[['The complete answer is rejected in 2 conversations. Their individual details are shown for inspection but are not counted as correct.']]);
det.getRange(`G6:G${de}`).conditionalFormats.add('cellIs',{operator:'equal',formula:'"Correct"',format:{fill:green}});
det.getRange(`G6:G${de}`).conditionalFormats.add('cellIs',{operator:'equal',formula:'"Incorrect"',format:{fill:red}});
det.getRange(`G6:G${de}`).conditionalFormats.add('containsText',{text:'review',format:{fill:amber}});
det.getRange(`G6:G${de}`).conditionalFormats.add('containsText',{text:'Unusable',format:{fill:red}});
const ce=table(conv,conversations,['Conversation','Correct details','Details checked','Correct %','Answer usable','Expected follow-up','Model follow-up','Model decision result','Decision after website checks','Result after website checks','Wrong sales referral by model','Wrong sales referral after checks','Details requiring attention'],[17,15,15,15,18,27,27,20,29,22,20,22,65],'Results for all 233 conversations','Website checks were tested using the saved model answers. This was not a live website test.','ConversationResults');
conv.getRange('D6').formulas=[['=B6/C6']];conv.getRange(`D6:D${ce}`).fillDown();conv.getRange(`D6:D${ce}`).setNumberFormat('0.0%');
base(summary,78,[48,18,18,18,65], 'Beacon response quality report','30 September 2026. Latest trained model. 233 English test conversations.');summary.freezePanes.freezeRows(0);
set(summary,'A3',[['Percentages show matches to prepared expected answers. They are not a live website confidence score.']]);
set(summary,'A4',[['Recommendation: improve the model before allowing it to make decisions on its own.']]);summary.getRange('A4:E4').format={fill:amber,rowHeight:29,font:{bold:true,color:navy}};
set(summary,'A6',[['Measure','Correct / count','Total checked','Percentage','What this means']]);head(summary,'A6:E6');
const metrics=[
 ['Individual details answered correctly',`=COUNTIFS('Answer details'!G6:G${de},"Correct")`,details.length,'Includes correctly leaving missing information unknown.'],
 ['Correct when expected information is available',`=COUNTIFS('Answer details'!G6:G${de},"Correct",'Answer details'!I6:I${de},"Yes")`,details.filter(x=>x[8]==='Yes').length,'Excludes details whose expected answer is unknown.'],
 ['Conversations with every checked detail correct',`=COUNTIFS('Conversation results'!B6:B${ce},22)`,233,'All 22 checked details must match in the same conversation.'],
 ['Correct model follow-up decisions',`=COUNTIFS('Conversation results'!H6:H${ce},"Correct")`,233,'Whether to send to sales, keep in touch, close or ask a person.'],
 ['Correct decisions after website checks',`=COUNTIFS('Conversation results'!J6:J${ce},"Correct")`,233,'Saved answers were passed through the website checks again.'],
 ['Wrong sales referrals by the model',`=COUNTIFS('Conversation results'!K6:K${ce},"Yes")`,233,'Lower is better. These visitors should not have been sent to sales.'],
 ['Wrong sales referrals after website checks',`=COUNTIFS('Conversation results'!L6:L${ce},"Yes")`,233,'Lower is better. Two mistakes remain even after the checks.'],
 ['Unusable complete answers',`=COUNTIFS('Conversation results'!E6:E${ce},"Unusable")`,233,'Lower is better. These answers cannot be accepted as supplied.']];
metrics.forEach((m,i)=>{let n=i+7;set(summary,`A${n}`,[[m[0],null,m[2],null,m[3]]]);summary.getRange(`B${n}`).formulas=[[m[1]]];summary.getRange(`D${n}`).formulas=[[`=B${n}/C${n}`]];});summary.getRange('D7:D14').setNumberFormat('0.0%');summary.getRange('A7:E14').format.wrapText=true;summary.getRange('A7:E14').format.rowHeight=48;
set(summary,'A16',[['Can we use it on the live website?']]);head(summary,'A16:E16');
const actions=[
 ['Use without a person checking?', 'Not recommended. Wrong sales decisions still remain.'],
 ['Use in a limited trial?', 'Only after connecting and testing it on the website, with a person approving each sales referral.'],
 ['More training needed?', 'Yes. First review the differing answers, then train on confirmed mistakes in visitor problems, names, permission and follow-up choices.'],
 ['Are all differences definitely wrong?', 'No. Some answers use different wording. Those are marked Needs wording review and are not counted as correct yet.'],
 ['How confident are we about live use?', 'A reliable live-use percentage is not yet available. These are prepared test conversations, not independently checked real customer chats.'],
 ['What was tested?', 'The model read each conversation and returned the details it understood and its follow-up decision. General customer-facing replies were not tested.'],
 ['What remains before launch?', 'Have a person review real customer conversations and expected answers. Retest after improvements, then check replies, waiting time and wrong sales referrals on the website.']];
actions.forEach((x,i)=>{let n=i+17;set(summary,`A${n}`,[[x[0]]]);summary.getRange(`B${n}:E${n}`).merge();set(summary,`B${n}`,[[x[1]]]);summary.getRange(`A${n}:E${n}`).format={wrapText:true,rowHeight:43};});
set(summary,'A25',[['Correct answers by question topic','Correct','Checked','Correct %','What was checked']]);head(summary,'A25:E25');
Object.entries(names).forEach(([key,name],i)=>{let n=i+26;set(summary,`A${n}`,[[name,null,233,null,rows[0].checks.find(c=>c.field===key).question.replace('ICP','lead suitability')]]);summary.getRange(`B${n}`).formulas=[[`=COUNTIFS('Answer details'!B6:B${de},A${n},'Answer details'!G6:G${de},"Correct")`]];summary.getRange(`D${n}`).formulas=[[`=B${n}/C${n}`]];});summary.getRange('D26:D47').setNumberFormat('0.0%');summary.getRange('A26:E47').format.wrapText=true;summary.getRange('A26:E47').format.rowHeight=37;
set(summary,'A49',[['How to read the results']]);head(summary,'A49:E49');
const notes=[
 'Questions and answers shows the actual Beacon questions, visitor replies, model findings and expected findings side by side.',
 'Answer details lists all 5,126 checks with the reason for each result. Conversation results shows each conversation percentage and follow-up decision.',
 'These percentages compare the model with prepared expected answers. Capital letters, extra spaces and list order do not affect the result. Different wording can still reduce the score.',
 'The expected answers have not all been checked by a person. These results should not be presented as a guaranteed percentage for live customers.',
 'The 233 conversations were not used for training. They are English examples and may share similar wording patterns. Hindi, Hinglish and real website conversations need separate testing.',
 'This report uses the completed 233-conversation test. All saved answers were checked again. The additional website-check test reused those answers and did not ask the model new questions.',
 'The latest trained model is not currently connected to the live website. Live reply quality and response time remain untested.'
];notes.forEach((t,i)=>{let n=i+50;summary.getRange(`A${n}:E${n}`).merge();set(summary,`A${n}`,[[t]]);summary.getRange(`A${n}:E${n}`).format={wrapText:true,rowHeight:38};});
book.recalculate();
const actual=summary.getRange('B7:B14').values.flat();const expected=[4693,3507,50,214,224,6,2,2];if(JSON.stringify(actual)!==JSON.stringify(expected))throw Error('Summary mismatch '+JSON.stringify(actual));
if(details.length!==5126||rows.length!==233)throw Error('Missing cases');
const statusCounts={};for(const d of details)statusCounts[d[6]]=(statusCounts[d[6]]??0)+1;
console.log(JSON.stringify({questions:questions.length,details:details.length,summary:actual,statusCounts}));
console.log((await book.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},summary:'Formula errors'})).ndjson);
for(const [sheetName,range,name]of [['Summary','A1:E14','manager-summary'],['Summary','A16:E23','manager-recommendation'],['Questions and answers','A5:F7','manager-questions'],['Answer details','A6:H8','manager-details']]){const img=await book.render({sheetName,range,scale:1.2,format:'png'});await fs.writeFile(path.join(dir,name+'.png'),new Uint8Array(await img.arrayBuffer()));}
const output=await SpreadsheetFile.exportXlsx(book);await output.save(path.join(dir,'Beacon_Manager_Detailed_Report.xlsx'));
await fs.writeFile(path.join(dir,'manager_report_checks.json'),JSON.stringify({questions:questions.length,details:details.length,summary:actual,statusCounts}));
console.log('Manager report saved.');
