"""CPU-only GPUP-ASSESS source bridge; measured workers and report stay immutable."""
from lp_protocol import ROOT,read_json,file_hash,checked_reference
RECEIPT=ROOT/'docs/benchmarks/data/assess/review-source.json'
ALLOWED={
 'crates/optimizer-experiment/src/lp_assess.rs',
 'crates/optimizer-experiment/examples/lp_precision_assess.rs',
 'tools/lp_assess_accept.py','tools/report_lp_assess.py',
 'tests/integration/test_lp_assess.py',
}
def review():
    if not RECEIPT.exists():return None
    r=read_json(RECEIPT)
    if r['identity']!='gpup-assess-cpu-review-v1' or r['gpu_seconds']!=0 or r['review_tool_sha256']!=file_hash(ROOT/'tools/lp_assess_review.py') or r['ledger_sha256']!='dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c':raise ValueError('assessment CPU review authority differs')
    files={f['path']:f for f in r['files']}
    if len(files)!=len(r['files']) or set(files)!=ALLOWED:raise ValueError('assessment CPU review file scope differs')
    for name,f in files.items():
        if file_hash(ROOT/name)!=f['reviewed_sha256']:raise ValueError('assessment undeclared review source '+name)
    checked_reference(ROOT,r['original_report']);checked_reference(ROOT,r['replay_audit'])
    return r

def projected_sha(name):
    r=review();current=file_hash(ROOT/name)
    if r:
        f=next((f for f in r['files'] if f['path']==name),None)
        if f:return f['measured_sha256']
    return current
