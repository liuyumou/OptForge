"""Source, binary, and resource bindings shared by the isolated GPUP-7R tools."""
from pathlib import Path
from benchmark_lp import source_identity,reference,prepare_execution
from lp_protocol import ROOT,file_hash,read_json,write_json
def numeric_sources():
    files=sorted({*ROOT.glob('crates/*/src/**/*.rs'),*ROOT.glob('cuda/**/*.cu'),ROOT/'crates/optimizer-experiment/examples/lp_precision_quant_resident.rs'})
    return {str(p.relative_to(ROOT)):file_hash(p) for p in files}
def freeze_cpu(directory,binary,image,device):
    base=dict(source_tree_sha256=source_identity(),binary_sha256=file_hash(binary),code_object_sha256=file_hash(image),highs_library_sha256=file_hash(ROOT/'target/native/highs-1.11.0/install/lib/libhighs.a'),device=device,cpu_affinity=[min(__import__('os').sched_getaffinity(0))],build_profile='release')
    prepare_execution(directory,base)
    if source_identity()!=base['source_tree_sha256']:raise ValueError('source changed while freezing CPU cohort')
    return read_json(directory/'execution.json')
