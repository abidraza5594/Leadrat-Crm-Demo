import json
from slm.prepare_v3 import expansion, fingerprint, OUT, read
from slm.build import check
from slm.labels import complete

def test_expansion_withdrawal_and_conflicts_are_not_positive_facts():
    rows=list(expansion())
    assert len(rows)==600
    for row in rows:
        q=complete(check(row))
        case=row['family'].split('/')[1]
        if case=='withdraw_consent':
            assert q.consent is False and q.route=='graceful_close'
        if case=='conflict_team':assert q.organisation.agents is None
        if case=='conflict_volume':assert q.monthly_leads.min is None
        if case=='beacon_suggestion':assert q.organisation.agents is None
        if case=='unknown_authority':assert q.influence=='unknown'
        if case=='partial':assert q.contact.email is None and q.next_step=='unknown'

def test_v3_split_integrity():
    sets={name:read(OUT/f'{name}.jsonl') for name in ['train','dev','test']}
    assert sum(r['language']=='en' for r in sets['train'])>2000
    for a,b in [('train','dev'),('train','test'),('dev','test')]:
        assert not {r['family'] for r in sets[a]} & {r['family'] for r in sets[b]}
        assert not {r['id'] for r in sets[a]} & {r['id'] for r in sets[b]}
        assert not {fingerprint(r) for r in sets[a]} & {fingerprint(r) for r in sets[b]}
