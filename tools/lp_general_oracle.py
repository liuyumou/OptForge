"""Independent exact-rational local products and original construction witnesses."""
import json
import argparse
import subprocess
from fractions import Fraction as Q
from pathlib import Path
from lp_general_common import ROOT, BASE, put, ref, require
from lp_general_models import generate

BINARY=ROOT/'research/lp-general-lowbit/target/release/lp-general-lowbit'


def settings(format='fp4x2'):
    return dict(format=format,tolerance=1e-9,iteration_limit=10000,check_interval=100,
        reference_window=16,wall_ms=30000,equilibrate=True)


def run(identity, image=None):
    directory=BASE/identity; directory.mkdir(parents=True,exist_ok=False)
    checked=0; requests=0
    for family in ['irregular','rectangular','dense_blocks','ill_scaled','degenerate','dense']:
        doc,witness=generate(family,33,790079)
        path=directory/(family+'.json'); put(path,doc)
        commands=[]
        for transpose in [False,True]:
            n=witness['rows'] if transpose else witness['columns']
            for magnitude in [0.,2.**-140,1.,2.**30]:
                anchor=[magnitude*((j%7)-3)/8 for j in range(n)]
                for near in [False,True]:
                    x=[a+((j%11)-5)*(2.**-35 if near else max(magnitude,1.))/32 for j,a in enumerate(anchor)]
                    for format in ['native','fp32','fp4x1','fp4x2']:
                        commands.append(dict(settings=settings(format),transpose=transpose,vector=x,anchor=anchor))
        command=[str(BINARY),'gpu-probe' if image else 'operator',str(path)]+([str(image)] if image else [])
        process=subprocess.run(command,
            input=''.join(json.dumps(c)+'\n' for c in commands),text=True,capture_output=True)
        put(directory/(family+'-requests.json'),commands)
        (directory/(family+'-stdout.jsonl')).write_text(process.stdout)
        (directory/(family+'-stderr.txt')).write_text(process.stderr)
        require(process.returncode==0,'product process failed')
        responses=[json.loads(line) for line in process.stdout.splitlines()]
        require(len(responses)==len(commands),'response coverage')
        for request,response in zip(commands,responses):
            op=response['operator']; matrix=op['columns' if request['transpose'] else 'rows']
            for i,(lo,hi) in enumerate(zip(matrix['offsets'],matrix['offsets'][1:])):
                exact=sum((Q(matrix['original'][j])*Q(request['vector'][matrix['indices'][j]]) for j in range(lo,hi)),Q(0))
                for field in ['product','native']:
                    observed=response[field]['values'][i]; bound=response[field]['bounds'][i]
                    require(abs(Q(observed)-exact)<=Q(bound),'rational original-product enclosure')
                checked+=1
            require(all(c&15 not in (1,9) and c>>4 not in (1,9) for c in op['codes']),'normal FP4 codec')
            require(all(op['columns']['original'][j]==op['rows']['original'][q] for j,q in enumerate(op['columns']['ids'])),'canonical transpose')
            requests+=1
        put(directory/(family+'-responses.json'),responses)
    put(directory/'result.json',dict(status='passed',requests=requests,products=checked,
        binary=ref(BINARY),oracle=ref(__file__),authority='fractions.Fraction exact scaled-original products',
        gpu_executed=bool(image),image=ref(image) if image else None))
    print(dict(requests=requests,products=checked),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--image',type=Path)
    a=p.parse_args();run(a.id,a.image)
