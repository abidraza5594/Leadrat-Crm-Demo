"""Publish measured v3 evaluation totals without changing adapter weights."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / '.venv/Lib/site-packages'))
from dotenv import dotenv_values
from huggingface_hub import HfApi, CommitOperationAdd

def main():
    out = ROOT / 'outputs/beacon-training-v3'
    meta = json.loads((out / 'evaluation/summary.json').read_text())
    rows = [json.loads(line) for line in (out / 'evaluation/predictions.jsonl').read_text('utf-8').splitlines()]
    assert len(rows) == meta['examples'] == 233
    assert all(r['revision'] == meta['release']['revision'] for r in rows)
    known = [c for r in rows for c in r['checks'] if c['reference_known']]
    metrics = [
        ('All 22 fields match', meta['fully_matched'], meta['examples']),
        ('Individual fields match, including unknowns', meta['matched_fields'], meta['total_fields']),
        ('Known-reference fields match', sum(c['correct'] for c in known), len(known)),
        ('Usable schema and visitor evidence IDs', meta['schema_valid'], meta['examples']),
        ('Raw route matches reference', meta['routing_correct'], meta['examples']),
        ('Incorrect sales handoffs', meta['unsafe_handoffs'], meta['examples']),
    ]
    lines = ['## Held-out evaluation of v3', '',
             f"Tested adapter revision: `{meta['release']['revision']}`.", '',
             '233 synthetic English conversations from 38 held-out scenario families; 22 reported fields per conversation.',
             'Test IDs, scenario families and exact visitor transcripts do not overlap the train/development splits.', '',
             '| Metric | Count | Rate |', '| --- | ---: | ---: |']
    lines += [f'| {name} | {n:,} / {d:,} | {n/d:.1%} |' for name, n, d in metrics]
    lines += ['', 'Matching uses normalized equality, not human semantic grading. Correct unknown values contribute to the overall field rate.',
              'Known-reference matching excludes null/unknown reference values. Valid paraphrases can count as mismatches.',
              'Full-match excludes evidence and rationale text. Incorrect handoffs mean sales_handoff when the reference is not sales_handoff or consent is absent.',
              'These results apply to structured qualification extraction, not general question-answer responses.',
              'Synthetic labels are not independently human-reviewed; real-customer performance and improvement over the old adapter are not established.',
              'See `eval_v3/summary.json` for the dataset hash, inference settings and measured totals.', '',
              'Files under `eval/` are historical results of the previous adapter.']
    card = (ROOT / 'slm/hf/README.md').read_text('utf-8')
    card = card.replace('Loss is not question-answer accuracy. The held-out evaluation is pending for this release.',
                        'Loss is not question-answer accuracy. See the held-out evaluation below.')
    card = card.split('## Evaluation and limitations')[0].split('## Held-out evaluation of v3')[0] + '\n'.join(lines) + '\n'
    api = HfApi(token=dotenv_values(ROOT / '.env').get('HF_TOKEN'))
    repo = meta['release']['repo']
    before = api.model_info(repo, files_metadata=True)
    expected = meta['release']['weights_sha256']
    assert next(s.lfs.sha256 for s in before.siblings if s.rfilename == 'adapter_model.safetensors') == expected
    commit = api.create_commit(repo_id=repo, parent_commit=before.sha,
        commit_message='Document v3 held-out evaluation on 233 English conversations',
        operations=[CommitOperationAdd(path_in_repo='README.md', path_or_fileobj=card.encode()),
                    CommitOperationAdd(path_in_repo='eval_v3/summary.json', path_or_fileobj=(out / 'evaluation/summary.json').read_bytes())])
    after = api.model_info(repo, revision=commit.oid, files_metadata=True)
    assert next(s.lfs.sha256 for s in after.siblings if s.rfilename == 'adapter_model.safetensors') == expected
    for p in [ROOT / 'slm/hf/README.md', out / 'hf-v3-release/README.md']:
        p.write_text(card, encoding='utf-8')
    result = {'revision': commit.oid, 'tested_weights_revision': meta['release']['revision'],
              'weights_sha256': expected, 'commit_url': str(commit.commit_url)}
    (out / 'hf_evaluation_published.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
