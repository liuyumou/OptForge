"""CPU-only ADR-0016 component measurements; preserve all prior diagnostic artifacts."""
import argparse
from pathlib import Path
import subprocess
import time
from benchmark_lp import source_identity
from benchmark_lp_matched import OUTPUT
from lp_protocol import ROOT, file_hash, read_json, write_json
from validate_artifacts import SchemaSnapshot, schema_snapshot


def measure(directory=OUTPUT):
    directory.mkdir(parents=True,exist_ok=True)
    binary=ROOT/'target/release/examples/lp_diagnose'
    result={'source_tree_sha256':source_identity(),'component_binary_sha256':file_hash(binary),'components':{},'schemas':{}}
    for name in ['small-4','irregular-256','irregular-2048','dense_block-1024']:
        model=ROOT/f'artifacts/lp-inputs-v1/gpup-development-{name}.json'
        endpoint=ROOT/f'artifacts/gpup-baseline-v1/profile-gpup-development-{name}-0-cuda-lp.endpoint.json'
        run=subprocess.run([str(binary),'cost',str(model),str(endpoint)],capture_output=True,text=True,check=True,timeout=30)
        import json
        result['components'][name]={'model_sha256':file_hash(model),'endpoint_sha256':file_hash(endpoint),
            'measurement':json.loads(run.stdout)}
    for kind,path in [('ledger',ROOT/'examples/lp-ledger-v1.synthetic.json'),
        ('endpoint',ROOT/'artifacts/gpup-baseline-v1/profile-gpup-development-irregular-2048-0-cuda-lp.endpoint.json')]:
        value=read_json(path);fresh=[];cached=[];name=f'lp-{kind}-v1.schema.json'
        reused=schema_snapshot().validator(name)
        for _ in range(3):
            start=time.perf_counter_ns();SchemaSnapshot().validator(name).validate(value);fresh.append(time.perf_counter_ns()-start)
            start=time.perf_counter_ns();reused.validate(value);cached.append(time.perf_counter_ns()-start)
        wrong={**value,'unknown':True}
        for check in [SchemaSnapshot().validator(name),reused]:
            try:check.validate(wrong)
            except Exception:pass
            else:raise AssertionError('schema strictness lost')
        result['schemas'][kind]={'fresh_snapshot_validation_ns':fresh,'reused_validation_ns':cached}
    result['schema_snapshot_sha256']=schema_snapshot().sha256
    write_json(directory/'cpu-components.json',result)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args();measure(args.output);print('CPU component costs retained')
