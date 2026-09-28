import copy
from slm.evaluate import load, metrics, ROOT

def rows(pred_fn):
    data = load(ROOT/'slm'/'data'/'dev.jsonl')
    return [{'id':r['id'],'pred':pred_fn(copy.deepcopy(r['gold'])),'reason':None,'gold':r['gold'],'ms':100,'usage':{}} for r in data]

def test_perfect_predictions_score_perfectly():
    m = metrics(rows(lambda g: g))
    assert m['schema_valid_pct'] == 100 and m['routing_accuracy_pct'] == 100 and m['macro_f1'] == 1.0 and m['unsafe_handoffs'] == 0
    assert all(v == 100 for v in m['field_accuracy_pct'].values())

def test_invalid_and_unsafe_are_counted():
    def spoil(g):
        g['route'] = 'sales_handoff'; return g
    m = metrics(rows(spoil))
    assert m['unsafe_handoffs'] > 0 and m['routing_accuracy_pct'] < 100
    m = metrics(rows(lambda g: None))
    assert m['schema_valid_pct'] == 0 and m['routing_accuracy_pct'] == 0
