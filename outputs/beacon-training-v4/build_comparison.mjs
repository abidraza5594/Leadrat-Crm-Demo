import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const dir='C:/Leadrat AI/Beacon/outputs/01a0f0f0-6c7c-7de2-a39a-3465964ea299';
const previewOnly=process.argv.includes('--preview');
const data=JSON.parse(await fs.readFile(new URL(previewOnly?'./comparison/report-data-preview.json':'./comparison/report-data.json',import.meta.url),'utf8'));
const wb=Workbook.create();
const sheets=Object.fromEntries(['Summary','By answer type','Answer comparison','Conversation results','Customer conversations'].map(n=>[n,wb.worksheets.add(n)]));
const ink='#24364B',blue='#294C71',light='#EDF2F7';
function setup(s,headers,rows,widths){
  s.showGridLines=false;s.getRangeByIndexes(0,0,rows.length+5,headers.length).format.font={name:'Arial',size:11,color:ink};
  s.getRange('A2').values=[[s.name]];s.getRange('A2').format.font={size:16,bold:true};
  s.getRangeByIndexes(4,0,1,headers.length).values=[headers];
  s.getRangeByIndexes(4,0,1,headers.length).format={fill:blue,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:36,verticalAlignment:'center',horizontalAlignment:'center'};
  if(rows.length)s.getRangeByIndexes(5,0,rows.length,headers.length).values=rows;
  s.getRangeByIndexes(5,0,Math.max(1,rows.length),headers.length).format={wrapText:true,verticalAlignment:'center',rowHeight:30};
  widths.forEach((w,i)=>s.getRangeByIndexes(0,i,rows.length+5,1).format.columnWidth=w);
  if(rows.length){const table=s.tables.add(`A5:${String.fromCharCode(64+headers.length)}${rows.length+5}`,true,s.name.replaceAll(' ','')+'Table');table.style='TableStyleMedium2';s.freezePanes.freezeRows(5);}
}
setup(sheets['Answer comparison'],['Case','Test group','Detail checked','Expected answer','Before training','After training','Before result','After result','Change','Explanation','Expected information available'],data.details,[10,18,32, forty(),forty(),forty(),15,15,20,55,18]);
function forty(){return 40;}
const detail=sheets['Answer comparison'];
detail.getRange('A5:K5').format.rowHeight=54;
detail.freezePanes.freezeColumns(2);
detail.getRange('A3').values=[['Match means the expected wording/value matched. Different valid wording can also need review.']];
detail.getRange(`G6:H${data.details.length+5}`).conditionalFormats.add('containsText',{text:'Review',format:{fill:'#FFF1D6',font:{color:'#754E0A'}}});
data.details.forEach((r,i)=>{const lines=Math.max(...[2,3,4,5,9].map(j=>String(r[j]).split('\n').reduce((n,line)=>n+Math.ceil(line.length/(j===9?75:50)),0)));if(lines>2)detail.getRangeByIndexes(i+5,0,1,11).format.rowHeight=Math.min(250,lines*15+8);});
setup(sheets['Conversation results'],['Case','Test group','Before matched details','After matched details','Details checked','Before complete answer','After complete answer','Expected follow-up','Before follow-up','After follow-up','Before follow-up correct','After follow-up correct','Before wrong sales referral','After wrong sales referral'],data.cases,[10,18,16,16,14,18,18,27,27,27,17,17,18,18]);
sheets['Conversation results'].getRange(`K6:N${data.cases.length+5}`).format.numberFormat='[=1]"Yes";[=0]"No"';
setup(sheets['Customer conversations'],['Case','Original test ID','Turn','Speaker','Exact conversation text'],data.turns,[10,32,9,14,115]);
sheets['Customer conversations'].getRange('A3').values=[['Prepared English conversations supplied to both models. Beacon lines here are test inputs, not newly generated replies.']];
data.turns.forEach((r,i)=>sheets['Customer conversations'].getRangeByIndexes(i+5,0,1,5).format.rowHeight=Math.max(30,Math.ceil(String(r[4]).length/145)*15+10));
setup(sheets['By answer type'],['Detail checked','Before matched','After matched','Checked','Before %','After %','Change (points)'],data.topics.map(x=>[x,0,0,0,0,0,0]),[39,18,18,14,16,16,20]);
const end=data.details.length+5,topic=sheets['By answer type'];
topic.getRange('A3').values=[['Same 233 comparison conversations. New examples are reported separately in Summary.']];
for(let i=0;i<data.topics.length;i++){
 let r=i+6;
 topic.getRange(`B${r}:G${r}`).formulas=[[
  `=COUNTIFS('Answer comparison'!$B$6:$B$${end},"Original 233",'Answer comparison'!$C$6:$C$${end},A${r},'Answer comparison'!$G$6:$G$${end},"Match")`,
  `=COUNTIFS('Answer comparison'!$B$6:$B$${end},"Original 233",'Answer comparison'!$C$6:$C$${end},A${r},'Answer comparison'!$H$6:$H$${end},"Match")`,
  `=COUNTIFS('Answer comparison'!$B$6:$B$${end},"Original 233",'Answer comparison'!$C$6:$C$${end},A${r})`,
  `=B${r}/D${r}`,`=C${r}/D${r}`,`=(F${r}-E${r})*100`]];
}
topic.getRange(`E6:F${data.topics.length+5}`).format.numberFormat='0.0%';
topic.getRange(`G6:G${data.topics.length+5}`).format.numberFormat='+0.0;-0.0;0.0';
topic.getRange(`G6:G${data.topics.length+5}`).conditionalFormats.add('cellIs',{operator:'lessThan',formula:0,format:{fill:'#FCE8E6',font:{color:'#A61B1B'}}});
const s=sheets.Summary;s.showGridLines=false;s.tabColor=blue;
s.getRange('A1:F52').format.font={name:'Arial',size:11,color:ink};
s.getRange('A1:A52').format.columnWidth=48;s.getRange('B1:D52').format.columnWidth=20;s.getRange('E1:F52').format.columnWidth=22;
s.getRange('A2').values=[['Beacon: before and after training']];s.getRange('A2').format.font={size:16,bold:true};
s.getRange('A3').values=[[previewOnly?'Layout preview using four completed smoke-test answers. Not a final report.':'1 October 2026. Same 233 prepared conversations compared with the previous saved results.']];
s.getRange('A5:D5').values=[['Measure','Before','After','Change']];s.getRange('A5:D5').format={fill:blue,font:{bold:true,color:'#FFFFFF'},rowHeight:28};
const n=data.cases.length+5;
const groups=['Original 233','New examples'];
const metrics=[['Details matching expected answers',6],['Known details matching expected answers',7],['Correct follow-up decisions',8],['Conversations with all details matching',9],['Unusable complete answers',10],['Wrong sales referrals',11]];
for(const [label,row] of metrics)s.getRange(`A${row}`).values=[[label]];
for(const [col,dcol,caseMatch,valid,route,unsafe] of [['B','G','C','F','K','M'],['C','H','D','G','L','N']]){
 s.getRange(`${col}6`).formulas=[[`=COUNTIFS('Answer comparison'!B6:B${end},"Original 233",'Answer comparison'!${dcol}6:${dcol}${end},"Match")/COUNTIFS('Answer comparison'!B6:B${end},"Original 233")`]];
 s.getRange(`${col}7`).formulas=[[`=COUNTIFS('Answer comparison'!B6:B${end},"Original 233",'Answer comparison'!${dcol}6:${dcol}${end},"Match",'Answer comparison'!K6:K${end},"Yes")/COUNTIFS('Answer comparison'!B6:B${end},"Original 233",'Answer comparison'!K6:K${end},"Yes")`]];
 s.getRange(`${col}8`).formulas=[[`=SUMIFS('Conversation results'!${route}6:${route}${n},'Conversation results'!B6:B${n},"Original 233")/COUNTIFS('Conversation results'!B6:B${n},"Original 233")`]];
 s.getRange(`${col}9`).formulas=[[`=COUNTIFS('Conversation results'!B6:B${n},"Original 233",'Conversation results'!${caseMatch}6:${caseMatch}${n},22)/COUNTIFS('Conversation results'!B6:B${n},"Original 233")`]];
 s.getRange(`${col}10`).formulas=[[`=COUNTIFS('Conversation results'!B6:B${n},"Original 233",'Conversation results'!${valid}6:${valid}${n},"Unusable")`]];
 s.getRange(`${col}11`).formulas=[[`=SUMIFS('Conversation results'!${unsafe}6:${unsafe}${n},'Conversation results'!B6:B${n},"Original 233")`]];
}
s.getRange('B6:C9').format.numberFormat='0.0%';
for(let r=6;r<=11;r++)s.getRange(`D${r}`).formulas=[[r<10?`=(C${r}-B${r})*100`:`=C${r}-B${r}`]];
s.getRange('D6:D9').format.numberFormat='+0.0" points";-0.0" points";0.0" points"';
s.getRange('A13').values=[['Additional new examples']];s.getRange('A13').format.font.bold=true;
s.getRange('A14:D14').values=[['Measure','Before','After','Change']];s.getRange('A14:D14').format={fill:blue,font:{bold:true,color:'#FFFFFF'}};
s.getRange('A15').values=[['Details matching expected answers']];
for(const [c,dc] of [['B','G'],['C','H']])s.getRange(`${c}15`).formulas=[[`=IF(COUNTIFS('Answer comparison'!B6:B${end},"New examples")=0,"n.a.",COUNTIFS('Answer comparison'!B6:B${end},"New examples",'Answer comparison'!${dc}6:${dc}${end},"Match")/COUNTIFS('Answer comparison'!B6:B${end},"New examples"))`]];
s.getRange('B15:C15').format.numberFormat='0.0%';s.getRange('D15').formulas=[['=IF(AND(ISNUMBER(B15),ISNUMBER(C15)),(C15-B15)*100,"n.a.")']];s.getRange('D15').format.numberFormat='+0.0" points";-0.0" points";0.0" points"';
s.getRange('A16').values=[['Correct follow-up decisions']];
for(const [col,route] of [['B','K'],['C','L']])s.getRange(`${col}16`).formulas=[[`=IF(COUNTIFS('Conversation results'!B6:B${n},"New examples")=0,"n.a.",SUMIFS('Conversation results'!${route}6:${route}${n},'Conversation results'!B6:B${n},"New examples")/COUNTIFS('Conversation results'!B6:B${n},"New examples"))`]];
s.getRange('B16:C16').format.numberFormat='0.0%';s.getRange('D16').formulas=[['=IF(AND(ISNUMBER(B16),ISNUMBER(C16)),(C16-B16)*100,"n.a.")']];s.getRange('D16').format.numberFormat='+0.0" points";-0.0" points";0.0" points"';
s.getRange('A18').values=[['What changed']];s.getRange('A18').format.font.bold=true;
data.notes.forEach((text,i)=>{const row=s.getRange(`A${19+i}:F${19+i}`);row.merge();s.getRange(`A${19+i}`).values=[[text]];row.format={wrapText:true,rowHeight:32,verticalAlignment:'center'};});
const vr=19+data.notes.length+2;
s.getRange(`A${vr}`).values=[['Training and publication record']];s.getRange(`A${vr}`).format.font.bold=true;
data.training.forEach((r,i)=>s.getRangeByIndexes(vr+i,0,1,3).values=[r]);
s.getRange(`A${vr+1}:C${vr+data.training.length}`).format={rowHeight:30,wrapText:true};
s.getRange('A5:D16').format.rowHeight=27;
await fs.mkdir(dir,{recursive:true});wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Summary!A5:D15',include:'values,formulas',tableMaxRows:12,tableMaxCols:4,maxChars:2800})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:20},summary:'Formula error scan'})).ndjson);
for(const [name,range] of [['Summary','A1:F16'],['By answer type','A1:G12'],['Answer comparison','A1:K9'],['Conversation results','A1:N9'],['Customer conversations','A1:E10']]){
 const preview=await wb.render({sheetName:name,range,scale:1,format:'png'});await fs.writeFile(`${dir}/v4-${name.replaceAll(' ','-')}.png`,new Uint8Array(await preview.arrayBuffer()));
}
const notesPreview=await wb.render({sheetName:'Summary',range:`A18:F${vr+data.training.length}`,scale:1,format:'png'});await fs.writeFile(`${dir}/v4-Summary-notes.png`,new Uint8Array(await notesPreview.arrayBuffer()));
if(!previewOnly){const file=await SpreadsheetFile.exportXlsx(wb);await file.save(`${dir}/Beacon_Before_After_Training.xlsx`);console.log('Saved comparison workbook');}
