import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const root='C:/Leadrat AI/Beacon';
const output=path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/,'$1'));
const folder=decodeURIComponent(output);
const evaluation=path.join(root,'outputs/beacon-training-v3/evaluation');
const rows=(await fs.readFile(path.join(evaluation,'predictions.jsonl'),'utf8')).trim().split('\n').map(JSON.parse);
const meta=JSON.parse(await fs.readFile(path.join(evaluation,'summary.json'),'utf8'));
if(rows.length!==233 || meta.examples!==233 || new Set(rows.map(r=>r.id)).size!==233)throw Error('Complete 233-case evaluation required');
if(rows.some(r=>r.revision!==meta.release.revision))throw Error('Mixed model revisions');
const book=Workbook.create();
const summary=book.worksheets.add('Summary');
const cases=book.worksheets.add('Conversations');
const fields=book.worksheets.add('Field results');
const methods=book.worksheets.add('Method and release');
const navy='#233449', muted='#EDF1F5', red='#FCE8E6';
const fieldRows=rows.flatMap(r=>r.checks.map(c=>[r.id,r.family,c.field,c.question,
 display(c.expected),r.valid?display(c.actual):rawAnswer(r,c.field),c.correct,c.reference_known,r.valid?c.method:`Output failed validation: ${r.parse_reason}`]));
function display(v){if(v===null)return 'Unknown (null)';if(Array.isArray(v))return v.length?JSON.stringify(v):'Explicitly none ([])';return v;}
function rawAnswer(r,field){try{let value=JSON.parse(r.raw);for(const key of field.split('.'))value=value?.[key];return value===undefined?'<missing field>':display(value);}catch{return '<unparseable JSON>';}}
function write(s,range,data){s.getRange(range).values=data;}
function header(s,range){s.getRange(range).format={fill:navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:32};}
function title(s,text){s.getRange('A2').values=[[text]];s.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:navy};s.getRange('A2:I2').format.rowHeight=28;}
function base(s,range){s.showGridLines=false;s.getRange(range).format={font:{name:'Arial',size:10,color:'#172B4D'},verticalAlignment:'center',rowHeight:22};}
const fend=fieldRows.length+5,cend=rows.length+5;
base(fields,`A1:I${fend}`);title(fields,'Question-by-question field results');
write(fields,'A3',[['Match = normalized equality to the reference. Different valid wording may be counted as a mismatch.']]);
write(fields,'A5:I5',[['Case ID','Scenario family','Field','Qualification question','Expected answer','Model answer','Match (1/0)','Known reference (1/0)','Comparison']]);
write(fields,`A6:I${fend}`,fieldRows);header(fields,'A5:I5');
const fw=[18,37,26,55,48,48,13,17,29];fw.forEach((w,i)=>fields.getRangeByIndexes(0,i,fend,1).format.columnWidth=w);
fields.getRange(`A6:I${fend}`).format.wrapText=true;
fields.getRange(`A6:I${fend}`).format.verticalAlignment='top';
fields.getRange(`A6:I${fend}`).format.rowHeight=42;
for(let i=0;i<fieldRows.length;i++){
 const r=fieldRows[i];const chars=Math.max(String(r[4]).length,String(r[5]).length);
 if(chars>80)fields.getRange(`A${i+6}:I${i+6}`).format.rowHeight=Math.min(130,Math.max(42,Math.ceil(chars/44)*13+8));
}
fields.tables.add(`A5:I${fend}`,true,'FieldResults');
fields.getRange(`G6:G${fend}`).conditionalFormats.add('cellIs',{operator:'equal',formula:0,format:{fill:red,font:{color:'#A32424',bold:true}}});
fields.freezePanes.freezeRows(5);fields.freezePanes.freezeColumns(1);

base(cases,`A1:U${cend}`);title(cases,'Conversation results and original answers');
write(cases,'A3',[['Full match requires all 22 reported fields to match. Raw output includes evidence and score rationale for inspection.']]);
write(cases,'A5:U5',[['Case ID','Scenario family','Language','Result','Matched fields','Fields checked','Field match %','Usable schema (1/0)','Expected route','Model route','Route match (1/0)','Unsafe handoff (1/0)','Model consistency','Mismatched fields','Questions asked','Visitor answers','Raw model answer (JSON)','Expected answer (JSON)','Parsed JSON match (1/0)','Rules-derived route','Batch time per case (s)']]);
const cd=rows.map(r=>[r.id,r.family,r.language,null,null,null,null,r.valid,r.gold.route,r.pred?.route??'<invalid>',r.routing_correct,r.unsafe_handoff,r.parse_reason??'ok',
 r.checks.filter(c=>!c.correct).map(c=>c.field).join(', ')||'None',r.prompt_questions,
 r.transcript.filter(t=>t.speaker==='visitor').map(t=>`[${t.turn_id}] ${t.text}`).join('\n'),r.raw,JSON.stringify(r.gold),r.raw_exact_json_match,r.rescored_route??'<invalid>',r.ms/1000]);
write(cases,`A6:U${cend}`,cd);header(cases,'A5:U5');
cases.getRange('D6:G6').formulas=[[
 '=IF(H6=0,"Invalid output",IF(E6=F6,"All fields match","Partial match"))',
 `=SUMIFS('Field results'!$G$6:$G$${fend},'Field results'!$A$6:$A$${fend},$A6)`,
 `=COUNTIFS('Field results'!$A$6:$A$${fend},$A6)`, '=E6/F6']];
cases.getRange(`D6:G${cend}`).fillDown();cases.getRange(`G6:G${cend}`).setNumberFormat('0.0%');cases.getRange(`U6:U${cend}`).setNumberFormat('0.0');
const cw=[18,37,10,20,12,12,14,15,20,20,15,15,24,48,70,95,115,115,15,20,19];cw.forEach((w,i)=>cases.getRangeByIndexes(0,i,cend,1).format.columnWidth=w);
cases.getRange(`A6:U${cend}`).format.wrapText=true;cases.getRange(`A6:U${cend}`).format.verticalAlignment='top';
for(let i=0;i<cd.length;i++){
 let lines=3;
 for(let c=13;c<18;c++)lines=Math.max(lines,...String(cd[i][c]).split('\n').map(t=>Math.ceil(t.length/(cw[c]-5))));
 const visitors=String(cd[i][15]).split('\n').reduce((n,t)=>n+Math.ceil(t.length/88),0);
 const questions=String(cd[i][14]).split('\n').reduce((n,t)=>n+Math.ceil(t.length/65),0);
 cases.getRange(`A${i+6}:U${i+6}`).format.rowHeight=Math.min(409,Math.max(lines,visitors,questions)*13+10);
}
cases.tables.add(`A5:U${cend}`,true,'ConversationResults');
cases.getRange(`D6:D${cend}`).conditionalFormats.add('containsText',{text:'Invalid',format:{fill:red,font:{color:'#A32424'}}});
cases.getRange(`L6:L${cend}`).conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0,format:{fill:red,font:{bold:true,color:'#A32424'}}});
cases.freezePanes.freezeRows(5);cases.freezePanes.freezeColumns(1);

base(summary,'A1:H52');title(summary,'Beacon v3 qualification evaluation');summary.tabColor=navy;
write(summary,'A4',[['30 September 2026. 233 held-out English conversations; published v3 adapter.']]);
write(summary,'A5',[['Reference matching results on synthetic data, not a general chatbot accuracy score.']]);
write(summary,'A7:D7',[['Metric','Matching / count','Evaluated','Rate']]);header(summary,'A7:D7');
const counts=[
 ['All 22 fields match',`=COUNTIFS('Conversations'!$D$6:$D$${cend},"All fields match")`,rows.length],
 ['Individual field answers match',`=SUM('Field results'!G6:G${fend})`,fieldRows.length],
 ['Usable schema and visitor evidence',`=SUM('Conversations'!H6:H${cend})`,rows.length],
 ['Correct raw routing decision',`=SUM('Conversations'!K6:K${cend})`,rows.length],
 ['Unsafe handoffs (lower is better)',`=SUM('Conversations'!L6:L${cend})`,rows.length],
 ['Score / route consistent with facts',`=COUNTIFS('Conversations'!M6:M${cend},"ok")`,rows.length],
 ['Parsed complete JSON match',`=SUM('Conversations'!S6:S${cend})`,rows.length],
 ['Known-reference field answers match',`=COUNTIFS('Field results'!G6:G${fend},1,'Field results'!H6:H${fend},1)`,fieldRows.reduce((n,r)=>n+r[7],0)]
];
counts.forEach((r,i)=>{let n=i+8;write(summary,`A${n}`,[[r[0]]]);summary.getRange(`B${n}`).formulas=[[r[1]]];write(summary,`C${n}`,[[r[2]]]);summary.getRange(`D${n}`).formulas=[[`=B${n}/C${n}`]];});
summary.getRange('D8:D15').setNumberFormat('0.0%');
summary.getRange('B8:C15').setNumberFormat('#,##0');
write(summary,'F7',[['Interpretation']]);summary.getRange('F7').format.font.bold=true;
const notes=[
 'Full match checks the 22 fields listed below.',
 'Field rate includes correctly unknown answers.',
 'Invalid outputs fail every field.',
 'Raw routing is scored before rule correction.',
 'Unsafe means a handoff disagrees with reference or lacks consent.',
 'Checks model scores and route against rules applied to predicted facts.',
 'Parsed JSON includes evidence and rationale.',
 'Excludes reference values marked unknown or null.'
];notes.forEach((t,i)=>write(summary,`F${i+8}`,[[t]]));
summary.getRange('F8:F15').format.wrapText=true;summary.getRange('A8:F15').format.rowHeight=34;
write(summary,'A17:F17',[['Qualification field','Matched','Total','Match %','Known answers','Known match %']]);header(summary,'A17:F17');
const names=Object.keys(meta.fields);
names.forEach((field,i)=>{
 const r=18+i;
 write(summary,`A${r}`,[[field]]);
 summary.getRange(`B${r}:F${r}`).formulas=[[
 `=SUMIFS('Field results'!$G$6:$G$${fend},'Field results'!$C$6:$C$${fend},$A${r})`,
 `=COUNTIFS('Field results'!$C$6:$C$${fend},$A${r})`,
 `=B${r}/C${r}`,
 `=SUMIFS('Field results'!$H$6:$H$${fend},'Field results'!$C$6:$C$${fend},$A${r})`,
 `=IF(E${r}=0,"n.a.",COUNTIFS('Field results'!$C$6:$C$${fend},$A${r},'Field results'!$G$6:$G$${fend},1,'Field results'!$H$6:$H$${fend},1)/E${r})`
 ]];
});
summary.getRange('D18:D39').setNumberFormat('0.0%');summary.getRange('F18:F39').setNumberFormat('0.0%');
write(summary,'A42',[['Known match % excludes references marked null or unknown. Empty lists mean explicitly none.']]);
write(summary,'A44',[['Text equality ignores case, whitespace and list order. Valid paraphrases can still be marked incorrect.']]);
write(summary,'A46',[['These results do not establish real-customer performance or prove improvement over the old adapter.']]);
const sw=[45,17,14,14,19,59,3,12];sw.forEach((w,i)=>summary.getRangeByIndexes(0,i,52,1).format.columnWidth=w);
summary.getRange('A17:F39').format.rowHeight=24;summary.getRange('A17:F17').format.rowHeight=38;
summary.getRange('A18:A39').format.font.bold=true;
summary.getRange('B18:C39').setNumberFormat('0');summary.getRange('E18:E39').setNumberFormat('0');

base(methods,'A1:B32');title(methods,'Evaluation method and model release');
const mr=[
 ['Model repository',`https://huggingface.co/${meta.release.repo}`],
 ['Tested revision',meta.release.revision],
 ['Weights SHA256',meta.release.weights_sha256],
 ['Training run','https://www.kaggle.com/code/abidrazaansari/beacon-v3-english-training?scriptVersionId=354072355'],
 ['Evaluation run',meta.evaluation_run_url],
 ['Training', 'Continued existing adapter; 2811 training conversations, 356 development conversations, 2 additional epochs, 352 steps.'],
 ['Evaluation set','233 synthetic held-out English conversations from 38 scenario families. No exact visitor-transcript, ID or family overlap with training or development.'],
 ['Test data SHA256',meta.test_sha256],
 ['Reference labels','Synthetic teacher and controlled scenario labels. Not independently reviewed by a human. Numerical scores and routes follow the project qualification rules.'],
 ['Inference',meta.inference],
 ['Hardware',meta.gpu],
 ['Task','Extract qualification facts and score/route a supplied conversation. This adapter is not a general customer-facing answer generator.'],
 ['Field match rule','Categorical, numerical, boolean and score-range values require equality. Text ignores case and repeated whitespace. Text lists ignore order and duplicates. Null and empty lists are different.'],
 ['Full-match definition','All 22 reported fields match. Evidence IDs and score-rationale content are excluded from this headline metric and included in parsed complete JSON match.'],
 ['Usable-schema definition','The project Qualification parser accepts the JSON and cited evidence turn IDs belong to visitors. This is not independent validation of every evidence claim.'],
 ['Raw vs corrected routing','The headline reports the raw model route. The Conversations sheet also shows a rules-derived route calculated from predicted facts.'],
 ['Time column','Batch wall time divided by number of cases. It is throughput-equivalent time, not single-request latency.'],
 ['Limitations',meta.limitations],
 ['Comparison with previous adapter','Not run on this evaluation set. Historical development results are not a comparable baseline.'],
 ['Follow-up needed','Review incorrect sales handoffs, score calculations and text mismatches. Test human-labelled customer conversations to measure real-customer performance.'],
 ['Review approach','Filter Field results by Match (1/0) = 0. Read expected and actual values beside each qualification question. Conversations preserves the original questions, visitor statements and raw JSON.']
];
write(methods,'A4:B4',[['Item','Details']]);write(methods,`A5:B${mr.length+4}`,mr);header(methods,'A4:B4');
methods.getRange('A1:A32').format.columnWidth=30;methods.getRange('B1:B32').format.columnWidth=120;
methods.getRange(`A5:B${mr.length+4}`).format.wrapText=true;methods.getRange(`A5:B${mr.length+4}`).format.verticalAlignment='top';
mr.forEach((r,i)=>methods.getRange(`A${i+5}:B${i+5}`).format.rowHeight=Math.max(30,Math.ceil(String(r[1]).length/110)*14+10));
book.recalculate();
const actual=summary.getRange('B8:B15').values.map(r=>r[0]);
const expected=[meta.fully_matched,meta.matched_fields,meta.schema_valid,meta.routing_correct,meta.unsafe_handoffs,rows.filter(r=>r.parse_reason===null).length,rows.reduce((n,r)=>n+r.raw_exact_json_match,0),fieldRows.reduce((n,r)=>n+(r[7]?r[6]:0),0)];
if(JSON.stringify(actual)!==JSON.stringify(expected))throw Error('Headline mismatch: '+JSON.stringify({actual,expected}));
for(let i=0;i<rows.length;i++)if(cases.getRange(`E${i+6}`).values[0][0]!==rows[i].matched_fields)throw Error('Case mismatch '+rows[i].id);
console.log((await book.inspect({kind:'table',range:'Summary!A7:D14',include:'values,formulas',tableMaxRows:8,tableMaxCols:4,maxChars:2500})).ndjson);
const errors=await book.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'Formula errors'});console.log(errors.ndjson);
const invalidStart=rows.findIndex(r=>!r.valid)*22+6;
for(const [s,range,name]of [[summary,'A1:F15','summary'],[cases,'Q5:R7','raw-answers'],[fields,`D${invalidStart}:I${invalidStart+3}`,'invalid-fields'],[methods,'A1:B13','method']]){
 const preview=await book.render({sheetName:s.name,range,scale:1.4,format:'png'});
 await fs.writeFile(path.join(folder,`${name}.png`),new Uint8Array(await preview.arrayBuffer()));
}
const xlsx=await SpreadsheetFile.exportXlsx(book);await xlsx.save(path.join(folder,'Beacon_v3_Evaluation_Report.xlsx'));
console.log('Report exported with '+rows.length+' conversations and '+fieldRows.length+' field answers.');
