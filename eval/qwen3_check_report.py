"""Summarize recorded inference; preserves the original scoring and raw outputs."""
import hashlib,html,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/qwen3-adapter-check-2026-10-08'
RUN=ROOT/'slm/runs/qwen3-17k-2026-10-08'

def main():
    rows=json.loads((OUT/'results.json').read_text('utf-8'))
    replay=json.loads((OUT/'conversation_replay.json').read_text('utf-8'))
    summary=json.loads((OUT/'summary.json').read_text('utf-8'))
    assert len(rows)==166 and len(replay)==19
    notes={
      'classify-9b196634c0bc4b768b71':'The visitor stated 12k monthly leads while the previous question asked team size. It was classified as a product question instead of customer information.',
      'demo_selection-e77ff6ffb3dd8ff1a966':'Email composition selected the general communication overview instead of the email action.',
      'demo_selection-fdcfcef7b52b85736a99':'Selected integrated WhatsApp chat instead of the general WhatsApp action. The catalogue contains overlapping descriptions; the refusal to open a demo WAS respected.',
      'demo_selection-b4d741e0a59278cf9e42':'Earlier lead activities selected Notes instead of History. These are different CRM operations.',
      'demo_selection-1668697457d37139f235':'Selected integrated WhatsApp chat instead of the general WhatsApp action. Overlapping catalogue descriptions need review.',
      'customer_update-7405419bb5d5933bc887':'Meaning retained: a different CRM. Shorter wording than the reference; this is not evidence the customer was misunderstood.',
      'customer_update-e66b91cebfbf492eee56':'Meaning retained: Excel. Shorter wording than the reference.',
      'customer_update-95129a89a998d772339c':'Correct developer value. Only the length of the supporting quote differs.',
      'customer_update-b74c776d835c97516b7f':'Correct brokerage value. Only the length of the supporting quote differs.',
      'customer_update-25254f0f22aa019cdd39':'Meaning retained. Capitalization differs. The application accepts case-insensitive evidence, while the raw exact-substring check does not.',
      'customer_update-fbd5e3a6e9a263bd2446':'Correct channel-partner value. Only the length of the supporting quote differs.',
      'customer_update-2bd71cffba35aab3e36a':'Meaning retained: immediately. Value and supporting quote differ, which can violate the application validation contract. See the separate diagnostic replay.',
      'manual work':'The reply manually was saved as the current working method instead of the pending problem field. This may leave the original question unanswered.',
    }
    review=[dict(id=r['id'],question=r['question'],expected=r['expected'],actual=r['actual'],note=notes.get(r['id'],'Review the expected and actual outputs.')) for r in rows if not r['passed']]
    (OUT/'reviewed_differences.json').write_text(json.dumps(review,indent=2,ensure_ascii=False),'utf-8')
    connected=replay[:13];diagnostics=replay[13:]
    verdict=dict(date='2026-10-08',adapter_integrity_verified=True,all_504_tensors_finite=True,
      adapter_sha256=hashlib.sha256((RUN/'adapter/adapter_model.safetensors').read_bytes()).hexdigest(),
      runtime='llama.cpp b11429 CUDA; Qwen3-4B-Instruct-2507 Q4_K_M base plus F32 converted LoRA, scale 1',
      sampled_test_examples=144,exact_test_matches=sum(r['passed'] for r in rows[:144]),
      existing_conversation_cases=22,existing_conversation_passed=sum(r['passed'] for r in rows[144:]),
      connected_turns=13,connected_turns_passed=sum(r['passed'] for r in connected),
      diagnostic_cases=6,diagnostic_cases_passed=sum(r['passed'] for r in diagnostics),
      full_website_tested=False,crm_clicks_tested=False,voice_tested=False,database_tested=False,
      deployed_to_website=False,production_ready_confirmed=False,
      limitations=['Synthetic test examples share construction patterns with training; not an independent real-customer benchmark.',
                  'Strict full-object matches include wording and evidence differences, not only semantic errors.',
                  '19 replay turns include diagnostic cases selected after initial failures; do not combine them into an overall accuracy.',
                  'Local evaluation uses a compact quantized base; it is not full-precision PEFT validation.',
                  'Existing 22 conversation tests assert decisions and selected facts, not every answer sentence or a real browser action.'])
    (OUT/'verification.json').write_text(json.dumps(verdict,indent=2),'utf-8')
    page=(OUT/'Beacon_Qwen3_Checks.html').read_text('utf-8')
    extra=['<h2>What the results mean</h2><p><strong>The adapter is intact and runs locally. Production readiness is not confirmed.</strong> The 70.8% customer-reply result is a strict wording-and-evidence match, not 70.8% semantic understanding. All seven mismatches retained the core meaning, but the immediate-timeline answer can fail the application validation rule.</p>',
           '<p>These synthetic examples share construction patterns with training. The 22 application checks verify decisions and selected facts, not every answer sentence or actual CRM clicks.</p>',
           '<h3>Reviewed differences</h3><ul>']
    for item in review:extra.append('<li>'+html.escape(item['note'])+'</li>')
    extra+=['</ul><h3>Connected conversation and diagnostic checks</h3>',f'<p>Connected conversation: {verdict["connected_turns_passed"]}/13 turns passed. Separate failure diagnostics: {verdict["diagnostic_cases_passed"]}/6. The replay carries actual previous model decisions and customer facts forward, with a fixed business-question sequence; it does not run the website or click the CRM.</p>']
    for row in replay:
        extra.append('<details><summary>'+html.escape(row['name']+' — '+row['message']+' — '+('Passed' if row['passed'] else 'Needs review'))+'</summary><pre>'+html.escape(json.dumps(row,indent=2,ensure_ascii=False))+'</pre></details>')
    page=page.replace('<h2>Every question and response</h2>','\n'.join(extra)+'<h2>Every question and response</h2>')
    (OUT/'Beacon_Qwen3_Checks.html').write_text(page,'utf-8')
    status_path=ROOT/'outputs/beacon-qwen3-fresh-training/kaggle-status.json'
    status=json.loads(status_path.read_text('utf-8'))
    status.update(local_download_verified=True,accuracy_evaluated=True,local_adapter=str((RUN/'adapter').relative_to(ROOT)),
      evaluation_scope='144 sampled held-out synthetic examples, 22 existing conversation cases, 13 connected turns and 6 targeted diagnostics; no live website test',
      evaluation_report=str((OUT/'verification.json').relative_to(ROOT)),production_ready_confirmed=False,deployed_to_website=False)
    status_path.write_text(json.dumps(status,indent=2),'utf-8')
    release_path=ROOT/'slm/current_release.json';release=json.loads(release_path.read_text('utf-8'))
    release.update(application_status='Old Qwen2.5 release retired. New Qwen3 adapter downloaded, integrity verified and evaluated locally; remaining behavior issues recorded. New adapter is not activated on the website.',
      candidate_adapter_path=str((RUN/'adapter').relative_to(ROOT)),candidate_evaluation=str((OUT/'verification.json').relative_to(ROOT)))
    release_path.write_text(json.dumps(release,indent=2),'utf-8')
    print(json.dumps(verdict,indent=2))

if __name__=='__main__':main()
