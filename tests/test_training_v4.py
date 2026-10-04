import hashlib,json
from pathlib import Path
from slm.prepare_v4 import make,read,fp,OUT

def test_contact_and_timing_do_not_create_false_handoffs():
    for j in range(20):
        for case in ['delayed_permission','withdraw_permission','chat_only','no_contact','decline']:
            q=make(case,j,'train')['target']
            assert q['route']!='sales_handoff'
        assert make('delayed_permission',j,'train')['target']['next_step']=='later'
        assert make('withdraw_permission',j,'train')['target']['consent'] is False
        for case in ['email_not_name','third_party_name']:
            assert make(case,j,'train')['target']['contact']['name'] is None

def test_corrections_conflicts_and_speaker_evidence():
    for j in range(20):
        for case in ['named_intro','named_late','name_correction']:
            q=make(case,j,'train')['target'];assert q['contact']['name']
        for case in ['team_conflict','beacon_only','unknown_team']:
            assert make(case,j,'train')['target']['organisation']['agents'] is None
        assert make('range_cross',j,'train')['target']['icp_score'] is None
        for case in ['lead_correction','name_correction','prompt_injection']:
            r=make(case,j,'train');visitors={t['turn_id'] for t in r['transcript'] if t['speaker']=='visitor'}
            assert all(set(ids)<=visitors for ids in r['target']['evidence'].values())

def test_preserved_baseline_and_split_separation():
    old=OUT.parent/'v3/test.jsonl'
    assert hashlib.sha256(old.read_bytes()).hexdigest()=='d93707cb1c105f98a5d4b46b0b38acc36bd2deae509a592207ae4020a4f25b10'
    splits={s:read(OUT/f'{s}.jsonl') for s in ['train','dev','fresh_test']}
    assert len(splits['train'])==10611
    seen={fp(r) for r in read(old)}
    for rs in splits.values():
        current={fp(r) for r in rs}
        assert len(current)==len(rs)
        assert not current&seen
        seen|=current
