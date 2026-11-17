"""Complete descriptive accounting; never turn an unsuccessful attempt into a speedup."""
import argparse
import statistics
from pathlib import Path
from lp_general_common import BASE,ROOT,load,put,ref,require


def analyze(identities,output):
    campaigns=[]
    for identity in identities:
        root=BASE/identity;f=load(root/'freeze.json');rows=[];missing=[]
        for c in f['cells']:
            path=root/f'm{c["model_index"]:02d}'/(c['id']+'.response.json')
            if not path.exists():missing.append(c['id']);continue
            r=load(path);raw=path.with_name(c['id']+'.stdout.jsonl');require(load(raw)==r,'raw response changed')
            require(r['certified']==(r['status']=='certified' and r['certificate']['accepted']),'certificate/status authority differs')
            if f['pilot']:require(r['physical']==500,'fixed-work pilot differs')
            job=BASE/'resources'/(identity+f'-m{c["model_index"]:02d}'+'.settlement.json')
            qualified=job.exists() and load(job)['status']=='passed'
            result_path=root/f'm{c["model_index"]:02d}'/'result.json'
            measurements=load(result_path)['rows'] if result_path.exists() else []
            measured=next((v for v in measurements if v['cell']['id']==c['id']),None)
            work=r['accepted_product_work']
            fields=['status','certified','logical','physical','accepted_product_work','physical_product_work','cost_ns','reference_product_nnz','recoveries','selected_initial_format','packed_bytes','operator_storage_bytes','tile_count']
            row={k:r[k] for k in fields}
            row.update(id=c['id'],model_index=c['model_index'],format=c['format'],tolerance=c['tolerance'],response=ref(path),
                supervised=qualified,complete_ms=measured['complete_ms'] if measured else None,
                useful_fp4_fraction=work[1]/work[3] if work[3] else 0,
                initial_fast_lanes=r.get('initial_fast_lanes'),nonzeros=r['nonzeros'])
            if c['command']=='gpu-fast':
                row['accepted_arithmetic_nnz']=dict(fp64=2*r['nonzeros']*r['accepted'][0],
                    fp32=2*r['nonzeros']*sum(r['accepted'][1:])-work[1],fp4_tensor=work[1])
            rows.append(row)
        formats=sorted({c['format'] for c in f['cells']});summaries=[]
        for fmt in formats:
            selected=[r for r in rows if r['format']==fmt]
            summaries.append(dict(format=fmt,planned=sum(c['format']==fmt for c in f['cells']),retained=len(selected),
                supervised=sum(r['supervised'] for r in selected),certified=sum(r['certified'] and r['supervised'] for r in selected),
                accepted_product_work=[sum(r['accepted_product_work'][j] for r in selected) for j in range(4)],
                recoveries=sum(len(r['recoveries']) for r in selected)))
        pairs=[]
        for r in rows:
            if r['format']=='native':continue
            # Match repeat/tier/model by the cell-id prefix; keep all outcomes.
            prefix=r['id'].rsplit('-'+r['format'],1)[0]
            native=next((v for v in rows if v['id']==prefix+'-native'),None)
            if not native:continue
            fp32=next((v for v in rows if v['id']==prefix+'-fp32'),None)
            certified=bool(native['certified'] and r['certified'] and native['supervised'] and r['supervised'])
            paired_time=native['complete_ms'] is not None and r['complete_ms'] is not None and native['supervised'] and r['supervised']
            paired_fp32=bool(fp32 and fp32['complete_ms'] is not None and r['complete_ms'] is not None and fp32['supervised'] and r['supervised'] and (f['pilot'] or (fp32['certified'] and r['certified'])))
            pairs.append(dict(id=r['id'],format=r['format'],model_index=r['model_index'],tolerance=r['tolerance'],jointly_certified=certified,
                fp4_nnz=r['accepted_product_work'][1],
                complete_ratio_native_over_candidate=(native['complete_ms']/r['complete_ms']) if paired_time and (certified or f['pilot']) else None,
                complete_ratio_fp32_over_candidate=fp32['complete_ms']/r['complete_ms'] if paired_fp32 else None,
                execution_ratio_native_over_candidate=native['cost_ns']['execution']/r['cost_ns']['execution'] if f['pilot'] and paired_time else None,
                native_logical=native['logical'],candidate_logical=r['logical'],claim='fixed-physical-work development' if f['pilot'] else 'jointly certified solve only'))
        comparison=[]
        for fmt in formats:
            selected=[r for r in pairs if r['format']==fmt and r['complete_ratio_native_over_candidate'] is not None]
            ratios=[r['complete_ratio_native_over_candidate'] for r in selected]
            fp32_pairs=[r for r in pairs if r['format']==fmt and r['complete_ratio_fp32_over_candidate'] is not None and fmt!='fp32']
            fp32_ratios=[r['complete_ratio_fp32_over_candidate'] for r in fp32_pairs]
            comparison.append(dict(format=fmt,pairs=len(ratios),faster=sum(v>1 for v in ratios),median_ratio=statistics.median(ratios) if ratios else None,
                actual_fp4_pairs=sum(r['fp4_nnz']>0 for r in selected),actual_fp4_faster=sum(r['fp4_nnz']>0 and r['complete_ratio_native_over_candidate']>1 for r in selected),
                fp32_pairs=len(fp32_ratios),fp32_median_ratio=statistics.median(fp32_ratios) if fp32_ratios else None,fp32_faster=sum(v>1 for v in fp32_ratios),
                actual_fp4_faster_than_fp32=sum(r['fp4_nnz']>0 and r['complete_ratio_fp32_over_candidate']>1 for r in fp32_pairs)))
        campaigns.append(dict(identity=identity,freeze=ref(root/'freeze.json'),pilot=f['pilot'],planned=len(f['cells']),retained=len(rows),missing=missing,rows=rows,summaries=summaries,pairs=pairs,comparisons=comparison))
        print(dict(campaign=identity,coverage=[len(rows),len(f['cells'])],summaries=summaries,comparisons=comparison),flush=True)
    put(output,dict(kind='fast-proposal-descriptive-results',campaigns=campaigns,source=ref(__file__),
        claim='No historical regrading, no confirmation or population superiority. All failures and missing cells remain.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ids',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();analyze(a.ids.split(','),a.output)
