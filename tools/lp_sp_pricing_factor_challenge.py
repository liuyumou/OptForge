"""Corruption checks on every accepted implicit endpoint in both holdouts."""
from pathlib import Path
import json
import numpy as np
from lp_sp_pricing_budget import ROOT,BASE,put,binding
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_factor_experiment import STUDY as PRIMARY,validate as primary
from lp_sp_pricing_transform_experiment import STUDY as FOLLOWUP,validate as followup
from lp_sp_pricing_factor_parallel_proof import verify_arrays
from lp_billion_arrays import read as read_array
from lp_billion_owned_process import execute
from lp_sp_pricing_baselines import PYTHON


def run():
    primary();followup();out=BASE/'factor-certificate-challenge-v1';out.mkdir(exist_ok=False);records=[]
    rows=[r for study,groups in ((PRIMARY,15),(FOLLOWUP,3)) for i in range(groups) for r in read(study/f'group-{i}.json')['rows']]
    controls=[]
    selected=[r for r in rows if r['lane']=='optimized' and r['seed']==124401 and r['family'] in ('mixed-tall-1m','mixed-tall-4m','mixed-tall-16m') and r['accepted']]
    put(out/'plan.json',dict(source=binding(__file__),serial_control_ids=[r['id'] for r in selected],
        policy='Cold serial checker controls on first optimized seed at all three unscaled tall sizes; compare exact results with the retained parallel proofs. Then challenge every accepted implicit holdout certificate twice.'))
    for row in selected:
        cert=read(row['reconstructed']['path']);prefix=out/('serial-'+row['id']);proof_path=Path(str(prefix)+'.json')
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_factor_proof.py'),cert['model']['path'],row['reconstructed']['path'],str(proof_path)]
        proc=execute(cmd,Path(str(prefix)+'.stdout'),Path(str(prefix)+'.stderr'),120,None)
        put(str(prefix)+'.process.json',proc)
        if proc['returncode'] or proc['timed_out'] or not proof_path.exists():raise RuntimeError('serial proof control failed')
        observed=read(proof_path);prior=read(row['proof']['path'])
        if not observed['accepted'] or any(observed[k]!=prior[k] for k in ('residual_numerator','residual_denominator_exponent','visited_nonzeros','primal_feasible','supported_on_exactly_active_rows')):raise ArithmeticError('large serial/parallel proof disagreement')
        controls.append(dict(id=row['id'],nonzeros=row['nonzeros'],parallel_process_ns=row['proof_ns'],serial_process_ns=proc['elapsed_ns'],
            serial_over_parallel=proc['elapsed_ns']/row['proof_ns'],serial_proof=binding(proof_path),parallel_proof=row['proof'],
            inverse_enclosures_bitwise_equal=observed['inverse_proof']==prior['inverse_proof'],
            disclosure='Same certificate, one later cold serial process; no cache flushing; no LP reexecution.'))
    for row in rows:
        if not row['accepted'] or not row.get('reconstructed'):continue
        cert=read(row['reconstructed']['path'])
        if not cert.get('implicit_certificate'):continue
        raw=read(cert['model']['path']);arrays={k:read_array(BASE,v) for k,v in raw['arrays'].items()};data=cert['implicit_certificate'];n=raw['columns']
        c=np.zeros(n);c[arrays['objective_indices']]=arrays['objective_values']
        x=read_array(BASE,data['primal']);y=read_array(BASE,data['dual_base']);basis=read_array(BASE,data['basis']);inverse=read_array(BASE,data['inverse']).reshape(n,n)
        args=[arrays['offsets'],arrays['indices'],arrays['values'],arrays['row_upper'],c,x,y,basis,inverse]
        bad_y=y.copy();bad_y[int(basis[0])]=-1.;negative=verify_arrays(*args[:6],bad_y,*args[7:])
        zero=verify_arrays(*args[:8],np.zeros_like(inverse))
        if negative['accepted'] or zero['accepted'] or zero.get('visited_nonzeros')!=row['nonzeros']:raise ArithmeticError('large corruption accepted or incompletely scanned')
        record=dict(id=row['id'],certificate=row['reconstructed'],negative_dual=negative,zero_inverse=zero)
        put(out/(row['id']+'.json'),record);records.append(binding(out/(row['id']+'.json')))
        print(json.dumps(dict(id=row['id'],checks=2,accepted_corruptions=0)),flush=True)
    put(out/'result.json',dict(status='passed',source=binding(__file__),serial_controls=controls,certificates=len(records),corruption_checks=2*len(records),records=records,
        scope='All accepted implicit certificates in the primary and fresh optimized holdout cohorts, including CPU and vendor controls; immutable inputs and original certificates unchanged.'))


if __name__=='__main__':run()
