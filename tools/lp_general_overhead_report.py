"""Descriptive matched schedule effects; no unsuccessful-solve speedup claims."""
import argparse
import json
import statistics
from pathlib import Path
from lp_general_common import BASE, ROOT, load, put, ref, require
from lp_general_fast_analyze import analyze


def report(identities, output):
    base_output = output.with_name(output.stem + '-base.json')
    analyze(identities, base_output)
    result = load(base_output)
    comparisons = []
    for identity in identities:
        f = load(BASE / identity / 'freeze.json')
        if not f['pilot']:
            continue
        rows = {r['cell']['id']: r for i in f['indices'] for r in load(BASE / identity / f'm{i:02d}' / 'result.json')['rows']}
        for i in f['indices']:
            for fmt in ['fp4x2', 'fp4x2-split']:
                pairs = []
                for c in f['cells']:
                    if c['model_index'] != i or c['format'] != fmt:
                        continue
                    key = c['id'].removesuffix(fmt)
                    old, new = rows[key + 'previous-' + fmt], rows[c['id']]
                    a, b = load(ROOT / old['response']['path']), load(ROOT / new['response']['path'])
                    canonical = lambda r: json.dumps({k:v for k,v in r.items() if k not in {'cost_ns', 'elapsed_ns', 'device_bytes_upper'}}, sort_keys=True, separators=(',', ':'))
                    require(canonical(a) == canonical(b), 'matched work changed ' + c['id'])
                    pairs.append(dict(before=old['response'], after=new['response'], exact=True,
                        execution_ratio=old['cost_ns']['execution']/new['cost_ns']['execution'],
                        complete_ratio=old['complete_ms']/new['complete_ms'],
                        before_execution_ms=old['cost_ns']['execution']/1e6, after_execution_ms=new['cost_ns']['execution']/1e6))
                comparisons.append(dict(model_index=i, format=fmt, pairs=pairs,
                    median_execution_ratio=statistics.median(p['execution_ratio'] for p in pairs),
                    median_complete_ratio=statistics.median(p['complete_ratio'] for p in pairs)))
    result['matched_version_comparisons'] = comparisons
    broad = [c for c in result['campaigns'] if not c['pilot']]
    if broad:
        rows = [r for c in broad for r in c['rows']]
        require(len({r['id'] for r in rows}) == len(rows), 'scientific cell repeated')
        original = load(BASE / 'fast-overhead-broad-v1/freeze.json')
        observed = {r['id'] for r in rows}
        summaries = []
        for fmt in ['native', 'fp32', 'fp4x2', 'fp4x2-split']:
            selected = [r for r in rows if r['format'] == fmt]
            pairs = [r for c in broad for r in c['pairs'] if r['format'] == fmt]
            native_ratios = [r['complete_ratio_native_over_candidate'] for r in pairs if r['complete_ratio_native_over_candidate'] is not None]
            fp32_ratios = [r['complete_ratio_fp32_over_candidate'] for r in pairs if r['complete_ratio_fp32_over_candidate'] is not None]
            work = [sum(r['accepted_product_work'][j] for r in selected) for j in range(4)]
            summaries.append(dict(format=fmt, responses=len(selected), timed=sum(r['supervised'] for r in selected),
                certified=sum(r['certified'] for r in selected), status_counts={s:sum(r['status']==s for r in selected) for s in sorted({r['status'] for r in selected})},
                accepted_product_work=work, accepted_fp4_share=work[1]/work[3] if work[3] else 0,
                native_pairs=len(native_ratios), native_ratio=statistics.median(native_ratios) if native_ratios else None,
                fp32_pairs=len(fp32_ratios), fp32_ratio=statistics.median(fp32_ratios) if fp32_ratios else None))
        result['consolidated_broad'] = dict(planned=len(original['cells']), responses=len(rows), timed=sum(r['supervised'] for r in rows),
            missing=[c['id'] for c in original['cells'] if c['id'] not in observed], summaries=summaries,
            claim='Distinct attempted cells only. Original stopped-cohort missingness remains in campaign records; tail covers never-started groups. Failed-group timings stay excluded.')
    result['report_source'] = ref(__file__)
    put(output, result)
    for c in result['campaigns']:
        print(c['identity'], c['retained'], '/', c['planned'])
    for r in comparisons:
        print(r['model_index'], r['format'], 'execution', round(r['median_execution_ratio'], 4), 'complete', round(r['median_complete_ratio'], 4))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--ids', nargs='+', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    report(a.ids, a.output)
