"""Materialize ADR-0014 LP inputs; --freeze writes first-version manifests/config."""
import argparse
import hashlib
from pathlib import Path
import subprocess
from lp_protocol import ROOT, PHASES, encoded, file_hash, read_json, write_json

FAMILIES = [('scheduling',[(20,5),(50,10)]),('irregular',[256,2048]),
            ('dense_block',[256,1024]),('scaling',[64,256]),('small',[4,16])]
PARTITIONS = {'development':17100,'validation':27100,'held_out':37100}
OUTPUT = ROOT / 'artifacts/lp-inputs-v1'

class Random:
    def __init__(self, seed): self.seed=seed; self.counter=0
    def integer(self, n):
        value = int.from_bytes(hashlib.sha256(f'{self.seed}:{self.counter}'.encode()).digest()[:8], 'big')
        self.counter += 1
        return value % n

def finite(x): return {'kind':'finite','value':float(x)}
def terms(row): return [{'variable_id':j,'coefficient':float(v)} for j,v in sorted(row.items()) if v]

def linear(identity, family, n, seed):
    rng = Random(seed)
    x = [0.0 if family == 'small' else float(j % 2) for j in range(n)]
    y = [float(1 + j % 3) * (1 if family == 'small' or j % 2 == 0 else -1) for j in range(n)]
    rows, costs = [], [1.0 if value == 0 else -1.0 for value in x]
    for i in range(n):
        if family == 'dense_block': indices = set(range(i//32*32, i//32*32+32)) | {(i+32)%n}
        elif family == 'small': indices = {i, (i+1)%n}
        else:
            width = min(n, 4+rng.integer(29)); indices={i}
            while len(indices) < width: indices.add(rng.integer(n))
        row={}
        for j in sorted(indices):
            value = 1 + rng.integer(4)
            if family != 'small' and rng.integer(2): value = -value
            if family == 'scaling': value *= 2.0 ** ((j+i)%41-20)
            row[j]=value
            costs[j] += y[i] * value
        activity = sum(row[j]*x[j] for j in row)
        lo,hi = (activity,activity+1) if y[i]>0 else (activity-1,activity)
        rows.append({'id':i,'lower':finite(lo),'upper':finite(hi),'terms':terms(row)})
    sense = 'maximize' if family == 'small' and n == 16 else 'minimize'
    sign = -1 if sense == 'maximize' else 1
    model={'schema_version':1,'model_id':identity,
        'variables':[{'id':j,'domain':'continuous','lower':finite(0),'upper':finite(1)} for j in range(n)],
        'constraints':rows,'objective':{'sense':sense,'offset':float(n)/4,
        'terms':terms({j:sign*v for j,v in enumerate(costs)})}}
    witness={'candidate':{'schema_version':1,'model_id':identity,
        'values':[{'variable_id':j,'value':v} for j,v in enumerate(x)]},'dual':y,
        'construction':'bounded primal/dual complementary pair; not a solver result'}
    return model,witness

def reference(path): return {'path':str(path.relative_to(ROOT)), 'sha256':file_hash(path)}

# ADR-0022 development extension: larger instances of existing families and a
# `mixed` family with equality/one-sided rows, free variables and coefficients that
# are exact in FP64 but inexact in FP32. Seeds occupy a separate band so no
# generator seed crosses partitions; groups are distinct from every v1 group.
EXTENSION=[('irregular',[32768,65536]),('dense_block',[65536]),('mixed',[65536])]
EXTENSION_SEED=17110
EXTENSION_LIMIT_SECONDS=30

def infinite(sign): return {'kind':'positive_infinity' if sign>0 else 'negative_infinity'}

def mixed(identity, n, seed):
    """Exact witness LP: equality, one-sided and ranged rows; boxed and free variables."""
    rng = Random(seed)
    free = [j % 10 == 3 for j in range(n)]
    # Free variables carry zero reduced cost; boxed variables sit at a bound.
    x = [float(rng.integer(3)-1) if free[j] else float(j % 2) for j in range(n)]
    rows, costs = [], [0.0 if free[j] else (1.0 if x[j] == 0.0 else -1.0) for j in range(n)]
    y = []
    for i in range(n):
        kind = i % 4  # 0 equality, 1 lower-only, 2 upper-only, 3 ranged
        magnitude = float(1 + i % 3)
        if kind == 0: yi = magnitude * (1 if i % 8 < 4 else -1)
        elif kind == 1: yi = magnitude
        elif kind == 2: yi = -magnitude
        else: yi = magnitude * (1 if i % 8 < 4 else -1)
        y.append(yi)
        width = min(n, 4+rng.integer(29)); indices={i}
        while len(indices) < width: indices.add(rng.integer(n))
        row={}
        for j in sorted(indices):
            # k + m*2^-30 with k in 1..4 and m in 1..7: exact binary64, inexact binary32.
            value = (1 + rng.integer(4)) + (1 + rng.integer(7)) * 2.0 ** -30
            if rng.integer(2): value = -value
            row[j]=value
            costs[j] += yi * value
        activity = sum(row[j]*x[j] for j in row)
        if kind == 0: lo, hi = finite(activity), finite(activity)
        elif kind == 1: lo, hi = finite(activity), infinite(+1)
        elif kind == 2: lo, hi = infinite(-1), finite(activity)
        else: lo, hi = (finite(activity), finite(activity+1)) if yi > 0 else (finite(activity-1), finite(activity))
        rows.append({'id':i,'lower':lo,'upper':hi,'terms':terms(row)})
    model={'schema_version':1,'model_id':identity,
        'variables':[{'id':j,'domain':'continuous','lower':infinite(-1) if free[j] else finite(0),
                      'upper':infinite(+1) if free[j] else finite(1)} for j in range(n)],
        'constraints':rows,'objective':{'sense':'minimize','offset':float(n)/4,'terms':terms(dict(enumerate(costs)))}}
    witness={'candidate':{'schema_version':1,'model_id':identity,
        'values':[{'variable_id':j,'value':v} for j,v in enumerate(x)]},'dual':y,
        'construction':'bounded/free primal and sign-matched dual complementary pair; not a solver result'}
    return model,witness

def extension(freeze=False):
    """Materialize the ADR-0022 development extension without touching v1 outputs."""
    OUTPUT.mkdir(parents=True,exist_ok=True)
    development=ROOT/'benchmarks/manifests/lp-development-v1.json'
    instances=[]
    for index,(family,sizes) in enumerate(EXTENSION):
        seed=EXTENSION_SEED+index
        for size in sizes:
            identity=f'gpup-extension-{family}-{size}'
            path=OUTPUT/(identity+'.json')
            if family == 'mixed': model,proof=mixed(identity,size,seed)
            else: model,proof=linear(identity,family,size,seed)
            if not path.exists() or read_json(path)!=model: write_json(path,model)
            proof_path=OUTPUT/(identity+'-witness.json')
            if not proof_path.exists() or read_json(proof_path)!=proof: write_json(proof_path,proof)
            instances.append({'id':identity,'family':family,'group':f'development-extension-{family}-{seed}',
                'model':reference(path),'bytes':path.stat().st_size,'witness':reference(proof_path),
                'source':'repository generation under ADR-0022',
                'license':'MIT repository generator; no third-party dataset redistribution',
                'generator':{'name':'sha256-counter-lp-v2','version':2,'seed':seed,'parameters':{'size':[size]}},
                'time_limit_seconds':EXTENSION_LIMIT_SECONDS})
    manifest={'schema_version':2,'id':'gpup-development-extension-v1','partition':'development',
              'extends':reference(development),'instances':instances}
    target=ROOT/'benchmarks/manifests/lp-development-extension-v1.json'
    if freeze:
        if target.exists() and read_json(target)!=manifest: raise ValueError('refusing to replace a frozen extension manifest')
        write_json(target,manifest)
    elif read_json(target)!=manifest: raise ValueError('generated extension differs from frozen manifest')
    return manifest

def generate(binary, freeze=False):
    OUTPUT.mkdir(parents=True,exist_ok=True)
    references=[]
    for partition,base in PARTITIONS.items():
        instances=[]
        for index,(family,sizes) in enumerate(FAMILIES):
            seed=base+index
            for size in sizes:
                label='x'.join(map(str,size)) if isinstance(size,tuple) else str(size)
                identity=f'gpup-{partition}-{family}-{label}'
                path=OUTPUT/(identity+'.json'); witness=None
                parameters={'size':list(size) if isinstance(size,tuple) else [size]}
                if family == 'scheduling':
                    instance=OUTPUT/(identity+'-flow-shop.json')
                    subprocess.run([str(binary),'schedule','generate','--instance-id',identity,
                        '--seed',str(seed),'--jobs',str(size[0]),'--machines',str(size[1]),'--output',str(instance)],check=True)
                    subprocess.run([str(binary),'lp-study','prepare','--instance',str(instance),'--output',str(path)],check=True)
                    generator='taillard-rust-positional-relaxation-v1'
                else:
                    model,proof=linear(identity,family,size,seed)
                    write_json(path,model)
                    proof_path=OUTPUT/(identity+'-witness.json'); write_json(proof_path,proof)
                    witness=reference(proof_path); generator='sha256-counter-lp-v1'
                instances.append({'id':identity,'family':family,'group':f'{partition}-{family}-{seed}',
                    'model':reference(path),'bytes':path.stat().st_size,'witness':witness,
                    'source':'repository generation under ADR-0014',
                    'license':'MIT repository generator; no third-party dataset redistribution',
                    'generator':{'name':generator,'version':1,'seed':seed,'parameters':parameters}})
        if partition == 'development':
            for name in ['ta001','ta011']:
                path=OUTPUT/(name+'-relaxation.json')
                subprocess.run([str(binary),'lp-study','prepare','--instance',str(ROOT/f'benchmarks/instances/flow-shop/{name}.json'),'--output',str(path)],check=True)
                instances.append({'id':name+'-relaxation','family':'taillard_diagnostic','group':name,
                    'model':reference(path),'bytes':path.stat().st_size,'witness':None,
                    'source':'benchmarks/manifests/taillard-flow-shop-development.json' if name=='ta001' else 'benchmarks/manifests/taillard-flow-shop-scale-v1.json',
                    'license':'Existing repository generated Taillard development diagnostic',
                    'generator':{'name':'rust-positional-relaxation-v1','version':1,'seed':0,'parameters':{'size':[]}}})
        manifest={'schema_version':1,'id':f'gpup-{partition}-v1','partition':partition,'instances':instances}
        target=ROOT/f'benchmarks/manifests/lp-{partition}-v1.json'
        if freeze:
            if target.exists() and read_json(target)!=manifest: raise ValueError('refusing to replace a frozen manifest')
            write_json(target,manifest)
        elif read_json(target)!=manifest: raise ValueError('generated inputs differ from frozen manifest')
        references.append(reference(target))
    solve=read_json(ROOT/'examples/solve-config-v1.json'); solve['iteration_limit']=50000
    value={'schema_version':1,'id':'gpup-baseline-v1','manifests':references,'partition':'development',
        'configurations':[{'id':b,'backend':b} for b in ['highs','host-lp','cuda-lp']],
        'solve':solve,'lp_settings':read_json(ROOT/'examples/lp-settings-v1.json'),
        'order_seed':17001,'repetitions':3,'profile_repetitions':1,
        'analysis':{'seed':17002,'resamples':10000,'confidence':0.95},
        'limits':{'solve_seconds':10,'cleanup_seconds':2,'host_rss_bytes':8*1024**3,
                  'device_buffer_bytes':8*1024**3,'poll_ms':10,'output_bytes':32*1024**2},
        'device':'GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48',
        'total_gpu_seconds':28800,'phase_gpu_seconds':PHASES,'slice_gpu_seconds':900}
    target=ROOT/'benchmarks/configs/lp-campaign-v1.json'
    if freeze:
        if target.exists() and read_json(target)!=value: raise ValueError('refusing to replace frozen campaign')
        write_json(target,value)
    elif read_json(target)!=value: raise ValueError('campaign differs from frozen generation')
    return value

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,default=ROOT/'target/debug/optimizer')
    parser.add_argument('--freeze',action='store_true')
    parser.add_argument('--extension',action='store_true',help='also materialize the ADR-0022 extension')
    args=parser.parse_args(); generate(args.binary.resolve(),args.freeze)
    if args.extension: extension(args.freeze)
