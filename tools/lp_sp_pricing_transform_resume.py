"""Read-only sweep seal and prospective untouched-holdout continuation."""
import argparse
import json
from pathlib import Path
from lp_sp_pricing_budget import ROOT,BASE,NS,put,binding
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_finish import identities,still_same_process
from lp_sp_pricing_transform_admit import validate as admission,sources
from lp_sp_pricing_factor_experiment import validate as primary,STUDY as PRIMARY
from lp_sp_pricing_transform_experiment import STUDY,SEEDS,FOLLOWUP_SPECS
from lp_sp_pricing_scale_experiment import generate
from lp_sp_pricing_factor_budget import allocation
from lp_sp_pricing_baselines import images

SEAL=BASE/'transform-selection-seal-v1'


def seal():
    admission();prefix=BASE/'resources/transform-selection-v1';receipt=read(str(prefix)+'.settlement.json');resource=read(str(prefix)+'.resource.json')
    if receipt['status']!='refused' or not receipt['cleanup_empty'] or receipt['overrun'] or receipt['cpu_ns']!=2400*NS or receipt['gpu_ns']!=600*NS or resource['result']['reason']!='coordinator_lost':raise RuntimeError('unexpected failure disposition')
    verify(receipt['resource']);reservation=read(str(prefix)+'.reservation.json')
    for source in reservation['sources']:
        retained=binding(source['retained'])
        if retained['sha256']!=source['sha256'] or retained['bytes']!=source['bytes']:raise ValueError('retained source')
    owned=set(identities(resource))|set(identities(read(str(prefix)+'.journal.json')))
    if any(still_same_process(*item) for item in owned):raise RuntimeError('selection identity remains')
    result=read(BASE/'transform-selection-v1/result.json');plan=read(BASE/'transform-selection-v1/plan.json')
    checked=bindings(result)+bindings(plan)
    expected={(family['name'],representation,multiplier) for family in plan['families'] for representation in plan['representations'] for multiplier in plan['multipliers']}
    observed={(row['family'],row['representation'],row['rho_multiplier']) for row in result['rows']}
    if len(result['rows'])!=24 or observed!=expected:raise ValueError('incomplete development roster')
    for row in result['rows']:
        proof=read(row['proof']['path']) if row.get('proof') else {}
        if row['accepted'] and (not proof.get('accepted') or proof.get('visited_nonzeros')!=row['nonzeros']):raise ValueError('incomplete retained proof')
    SEAL.mkdir(exist_ok=False)
    put(SEAL/'result.json',dict(status='completed_records_sealed_supervision_not_regraded',source=binding(__file__),
        original_failure=binding(str(prefix)+'.settlement.json'),result=binding(BASE/'transform-selection-v1/result.json'),plan=binding(BASE/'transform-selection-v1/plan.json'),
        checked_bindings=checked,recorded_identities=len(owned),live_owned_identities=[],numerical_recomputation=False,
        timing_excluded=True,original_failure_regraded=False,full_cpu_seconds=2400,full_gpu_seconds=600,preceding_cause='not established',
        prospective_choice=dict(representation=result['representation'],rho_multiplier=result['rho_multiplier']),
        choice_disclosure='Retain the exploratory choice as a hypothesis. Failed sweep timings are not eligible performance measurements; independent untouched holdouts determine performance.'))


def checked():
    d=read(SEAL/'result.json');bindings(d)
    if read(BASE/'resources/transform-selection-seal-v1.settlement.json')['status']!='passed':raise RuntimeError('seal supervision')
    return d


def freeze():
    gate=admission();primary();proof=checked();selection=read(BASE/'transform-selection-v1/result.json');STUDY.mkdir(exist_ok=False);models=[]
    for seed in SEEDS:
        for spec in FOLLOWUP_SPECS:models.append(generate(spec,seed,STUDY/'models'/f"{spec['name']}-{seed}"))
    put(STUDY/'freeze.json',dict(status='frozen',admission=gate,primary=binding(PRIMARY/'freeze.json'),models=models,
        sources=sources()+[binding(ROOT/'tools'/name) for name in ('lp_sp_pricing_transform_endpoint.py','lp_sp_pricing_transform_experiment.py','lp_sp_pricing_transform_resume.py')]+[binding(SEAL/'result.json'),binding(BASE/'resources/transform-selection-seal-v1.settlement.json')],
        native_seconds=60,process_seconds=90,postprocess_seconds=90,proof_seconds=120,
        selection=binding(BASE/'transform-selection-v1/result.json'),selection_seal=binding(SEAL/'result.json'),selection_timings_eligible=False,
        rho_multiplier=selection['rho_multiplier'],representation=selection['representation'],lanes=['optimized','factor','copt-gpu-1e9'],images=images(),wall_deadline_utc=allocation()['wall_deadline_utc'],
        additional_control='Each row-scaled tall holdout also runs installed-default Scaling GPU PDLP, Presolve=0, PDLPTol=1e-9.',
        disclosure='Only untouched holdout cells continue. Numerical, resource and certificate sources remain exact. Completed development sweep failed final supervision; full charge and timing exclusions remain. Its selected representation/penalty is an exploratory hypothesis, not a certified timing optimum.',
        memory_tradeoff='Precomputed representation stores another m*n FP64 entries; selected factor representation avoids that allocation.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['seal','freeze']);a=p.parse_args()
    seal() if a.action=='seal' else freeze()
