"""SPEC-0019 separate loadMatrix worker; historical scalar worker remains unchanged."""
import argparse
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from lp_protocol import file_hash,read_json,write_json
from lp_copt import gpu_started,validate_import_coefficients,parameters as old_parameters
from lp_cost import Profile
from lp_copt_matrix import prepare, load

METHODS=('copt-cpu-default','copt-cpu-pdlp','copt-gpu-pdlp')

def parameters(options,method):
    if method not in METHODS:raise ValueError('unknown COPT method')
    result=old_parameters(options,method=='copt-gpu-pdlp')
    if method=='copt-cpu-default':
        result.update(LpMethod=-1,Crossover=1);del result['PDLPTol']
    return result

def log_observations(lines):
    text='\n'.join(v['message'] for v in lines)
    patterns=[r'(?:presolved|reduced)\s+(?:LP|problem|model)(?:\s+has)?\s*:?\s*(\d+)\s+rows?,?\s+(\d+)\s+columns?\s+(?:and\s+)?(\d+)\s+(?:nonzeros|non-zero)',
              r'(\d+)\s+rows?,\s*(\d+)\s+columns?,\s*(\d+)\s+nonzeros']
    dimensions=None
    for pattern in patterns:
        found=re.findall(pattern,text,re.I)
        if found:dimensions=dict(zip(['rows','columns','nonzeros'],map(int,found[-1])));break
    return dict(presolved_dimensions=dimensions,resolution='coarse native logs; callback timestamps are delivery times, not exact phase boundaries',
                native_phases_opaque=['presolve','scaling','CPU iteration internals'],lines=lines)

def run(a):
    gpu=a.method=='copt-gpu-pdlp'
    if gpu and (os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited' or os.environ.get('CUDA_VISIBLE_DEVICES')!=a.device):
        raise ValueError('COPT GPU requires inherited shared lease and pinned UUID')
    profile=Profile(a.cost_profile is not None);lines=[];observations={}
    root=Path(sys.prefix)/'lib/python3.11/site-packages/coptpy'
    with profile.scope('copt'):
        with profile.scope('input_read_parse'):
            if a.model.stat().st_size>134217728:raise ValueError('study input exceeds 128 MiB')
            doc=read_json(a.model);options=read_json(a.config)
            doc['variables'].sort(key=lambda v:v['id']);doc['constraints'].sort(key=lambda r:r['id'])
        params=parameters(options,a.method)
        witness=dict(schema_version=2,model_sha256=file_hash(a.model),requested_backend=a.method,executed_backend=None,
            options=options,copt_version='8.0.6',parameters=params,library_sha256=file_hash(root/'libcopt_python.so'),
            binding_sha256=file_hash(root/'coptcore.so'),gpu_confirmed=False,row_ids=[r['id'] for r in doc['constraints']],
            variable_ids=[v['id'] for v in doc['variables']],primal=None,dual=None,status='backend_failure',iterations=None,native=None,
            limitations=['COPT exposes no matching hard PDLP iteration/seed controls; aggregate native iterations above 50000 are work-limited and are not project physical updates.'])
        model=None;env=None
        try:
            with profile.scope('import_bindings'):import coptpy as cp
            with profile.scope('input_range_guards'):validate_import_coefficients(doc)
            with profile.scope('environment_license'):env=cp.Envr()
            with profile.scope('model_creation'):model=env.createModel('gpup-copt-comparison-v1')
            class Log(cp.LogCallback):
                def Display(self,message):
                    lines.append(dict(message=message,delivered_ns=time.monotonic_ns()-profile.origin if profile.enabled else None))
            logger=Log();model.setLogCallback(logger)
            with profile.scope('parameter_setup'):
                for name,value in params.items():model.setParam(name,value)
            signal.signal(signal.SIGINT,lambda *_:model.interrupt())
            with profile.scope('sparse_dependency_import'):
                from scipy import sparse
            with profile.scope('sparse_preparation'):
                data = prepare(doc, cp.COPT.INFINITY)
            with profile.scope('bulk_model_construction'):
                load(cp, model, data, sparse)
            obj = doc['objective']
            with profile.scope('native_solve_call'):model.solveLP()
            with profile.scope('witness_extraction'):
                confirmed=gpu_started('\n'.join(v['message'] for v in lines))
                native=dict(simplex_iterations=int(model.getAttr('SimplexIter')),barrier_iterations=int(model.getAttr('BarrierIter')),
                    pdlp_iterations=int(model.getAttr('PDLPIter')),solving_seconds=float(model.getAttr('SolvingTime')),peak_memory_mb=float(model.getAttr('MemPeak')))
                status=model.getAttr('LpStatus')
                witness.update(native=native,iterations=sum(native[k] for k in ['simplex_iterations','barrier_iterations','pdlp_iterations']),gpu_confirmed=confirmed,
                    executed_backend=a.method if not gpu or confirmed else 'copt-cpu-pdlp',
                    status={cp.COPT.OPTIMAL:'optimal',cp.COPT.TIMEOUT:'time_limit',cp.COPT.INTERRUPTED:'interrupted',cp.COPT.ITERLIMIT:'iteration_limit'}.get(status,'numerical_failure'))
                if model.getAttr('HasLpSol'):
                    witness['primal']=list(model.getValues());sign=1 if obj['sense']=='minimize' else -1
                    witness['dual']=[sign*v for v in model.getDuals()]
        except Exception as error:
            witness['status']='unsupported' if isinstance(error,ValueError) else 'backend_failure'
            witness['limitations'].append(type(error).__name__+': '+str(error))
        with profile.scope('witness_output'):
            a.output.with_suffix('.copt.log').write_text('\n'.join(v['message'] for v in lines))
            wp=a.output.with_suffix('.witness.json');write_json(wp,witness)
        child=a.output.with_suffix('.cert-cost.json')
        with profile.scope('host_certification'):
            command=[str(a.binary),'lp-study','external-certify','--model',str(a.model),'--model-byte-limit','134217728','--evidence',str(wp),'--output',str(a.output)]
            if profile.enabled:command+=['--cost-profile',str(child)]
            certified=subprocess.run(command,check=False)
        with profile.scope('native_teardown'):
            # Binding reference release is measurable; final native destruction may
            # extend into the enclosing process teardown residual.
            del model;del env
            profile.unavailable.append('Native destruction beyond Python reference release is included only in the process teardown residual.') if profile.enabled else None
        observations=dict(original_dimensions=dict(rows=len(doc['constraints']),columns=len(doc['variables']),nonzeros=sum(len(r['terms']) for r in doc['constraints'])),
                          native=witness['native'],log_observations=log_observations(lines))
    if profile.enabled:
        write_json(a.cost_profile,profile.finish())
        write_json(a.output.with_suffix('.copt-observations.json'),observations)
    if certified.returncode:raise SystemExit(certified.returncode)
    print('COPT',a.method,witness['status'],witness['executed_backend'])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['model','config','output','binary']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--method',choices=METHODS,required=True);p.add_argument('--device',default='cpu')
    p.add_argument('--cost-profile',type=Path);run(p.parse_args())
if __name__=='__main__':main()
