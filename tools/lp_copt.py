"""Isolated COPT 8.0.6 PDLP witness producer. Not a runtime backend or SDK."""
import argparse, hashlib, math, os, re, signal, subprocess, sys
from pathlib import Path
from lp_protocol import read_json, write_json, file_hash

def gpu_started(log):
    return re.search(r"Starting PDLP solver (?:on|using) GPU 0\b",log) is not None

def validate_import_coefficients(doc):
    # COPT 8.0.6 defaults MatrixTol to 1e-10. Refuse input that this
    # installation could discard; the frozen study models all exceed it.
    terms=[t for row in doc['constraints'] for t in row['terms']]+doc['objective']['terms']
    if any(not math.isfinite(t['coefficient']) or 0 < abs(t['coefficient']) <= 1e-10 for t in terms):
        raise ValueError('coefficient outside the preserved COPT input range (MatrixTol=1e-10)')

def parameters(options,gpu):
    return dict(LpMethod=6,GPUMode=int(gpu),GPUDevice=0,Threads=1,Crossover=0,
                TimeLimit=options['time_limit_ms']/1000,PDLPTol=options['tolerances']['absolute'],
                FeasTol=options['tolerances']['absolute'],DualTol=options['tolerances']['absolute'])

def run(model_path,config_path,gpu,device,output,binary):
    if gpu and (os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited' or os.environ.get('CUDA_VISIBLE_DEVICES')!=device):
        raise ValueError('COPT GPU requires the inherited shared host lease and pinned UUID')
    import coptpy as cp
    doc=read_json(model_path);doc['variables'].sort(key=lambda v:v['id']);doc['constraints'].sort(key=lambda r:r['id']);options=read_json(config_path);params=parameters(options,gpu)
    root=Path(cp.__file__).parent
    witness=dict(schema_version=1,model_sha256=file_hash(model_path),requested_backend='copt-gpu-pdlp' if gpu else 'copt-cpu-pdlp',
        executed_backend=None,options=options,copt_version='8.0.6',parameters=params,
        library_sha256=file_hash(root/'libcopt_python.so'),binding_sha256=file_hash(root/'coptcore.so'),gpu_confirmed=False,
        row_ids=[r['id'] for r in doc['constraints']],variable_ids=[v['id'] for v in doc['variables']],primal=None,dual=None,
        status='backend_failure',iterations=None,limitations=['COPT 8.0.6 exposes no PDLP iteration-limit or random-seed parameter; wall limit is enforced; excess reported iterations are classified work_limit.'])
    lines=[]
    try:
        validate_import_coefficients(doc)
        env=cp.Envr();model=env.createModel('gpup5')
        class Log(cp.LogCallback):
            def Display(self,message):lines.append(message)
        logger=Log();model.setLogCallback(logger)
        for name,value in params.items():model.setParam(name,value)
        signal.signal(signal.SIGINT,lambda *_:model.interrupt())
        infinity=cp.COPT.INFINITY
        def bound(b):
            if b['kind']=='finite':
                if abs(b['value'])>=infinity:raise ValueError('finite bound exceeds COPT infinity sentinel')
                return b['value']
            return infinity if b['kind']=='positive_infinity' else -infinity
        variables={v['id']:model.addVar(lb=bound(v['lower']),ub=bound(v['upper']),name='v'+str(v['id'])) for v in doc['variables']}
        if any(v['domain']!='continuous' for v in doc['variables']):raise ValueError('external LP requires continuous variables')
        for r in doc['constraints']:
            expr=cp.LinExpr([variables[t['variable_id']] for t in r['terms']],[t['coefficient'] for t in r['terms']])
            model.addBoundConstr(expr,lb=bound(r['lower']),ub=bound(r['upper']),name='r'+str(r['id']))
        obj=doc['objective'];expr=cp.LinExpr([variables[t['variable_id']] for t in obj['terms']],[t['coefficient'] for t in obj['terms']])
        expr.addConstant(obj['offset']);model.setObjective(expr,cp.COPT.MINIMIZE if obj['sense']=='minimize' else cp.COPT.MAXIMIZE)
        model.solveLP()
        log='\n'.join(lines);gpu_confirmed=gpu_started(log)
        witness.update(gpu_confirmed=gpu_confirmed,executed_backend='copt-gpu-pdlp' if gpu_confirmed else 'copt-cpu-pdlp',iterations=int(model.getAttr('PDLPIter')))
        status=model.getAttr('LpStatus')
        witness['status']={cp.COPT.OPTIMAL:'optimal',cp.COPT.TIMEOUT:'time_limit',cp.COPT.INTERRUPTED:'interrupted',cp.COPT.ITERLIMIT:'iteration_limit'}.get(status,'numerical_failure')
        if model.getAttr('HasLpSol'):
            witness['primal']=list(model.getValues());sign=1 if obj['sense']=='minimize' else -1
            witness['dual']=[sign*v for v in model.getDuals()]
    except Exception as error:
        if isinstance(error,ValueError):witness['status']='unsupported'
        witness['limitations'].append(type(error).__name__+': '+str(error))
    log_path=output.with_suffix('.copt.log');log_path.write_text('\n'.join(lines))
    witness_path=output.with_suffix('.witness.json');write_json(witness_path,witness)
    subprocess.run([str(binary),'lp-study','external-certify','--model',str(model_path),'--evidence',str(witness_path),'--output',str(output)],check=True)
    print('COPT witness:',witness['status'],'executed:',witness['executed_backend'])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['model','config','output','binary']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--device',default='cpu');p.add_argument('--gpu',action='store_true');a=p.parse_args()
    run(a.model,a.config,a.gpu,a.device,a.output,a.binary)
if __name__=='__main__':main()
