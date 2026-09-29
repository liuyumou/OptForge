"""Materialize CPU-only repository evidence from the independently checked setup report."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
from lp_protocol import ROOT, file_hash, read_json, write_json


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plot', action='store_true', help='use separately provisioned Matplotlib for the standalone SVG')
    args = parser.parse_args()
    source = ROOT / 'artifacts/gpup-setup-v1'
    output = ROOT / 'docs/benchmarks/data/setup'; output.mkdir(parents=True, exist_ok=True)
    report = read_json(source / 'report.json')
    if (report['attempted'], report['verified'], report['certified']) != (32, 32, 24):
        raise ValueError('export expects the complete frozen study; preserve incomplete reports separately')
    write_json(output / 'setup-summary.json', {k: report[k] for k in ['id', 'planned', 'attempted', 'verified', 'certified', 'groups', 'ratios', 'equivalence', 'budget', 'limitations']})
    with (output / 'setup-trials.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(report['rows'][0]), lineterminator='\n');writer.writeheader();writer.writerows(report['rows'])
    write_json(output / 'setup-profiles.json', report['profiles'])
    (output / 'setup-analysis.json.gz').write_bytes(gzip.compress((source / 'report.json').read_bytes(), mtime=0))
    write_json(output / 'setup-control-attribution.json', read_json(source / 'control-attribution.json'))
    profiles = []
    for row in report['profiles']:
        values = row['scopes']
        scope = lambda name: values.get(name, {}).get('exclusive_ns', 0)
        phases = dict(discovery=scope('device_discovery'), driver_initialization=scope('driver_initialization'),
            context_open=scope('context_create_api')+scope('primary_retain_api'),
            context_close=scope('context_teardown')+scope('primary_detach_api')+scope('primary_release_api')+scope('primary_cleanup_check'),
            module=scope('module_load')+scope('module_load_api')+scope('module_image_preparation')+scope('module_unload'))
        timing = next(g for g in report['groups'] if all(g[k] == row[k] for k in ['instance_id', 'policy_id', 'variant']))
        profiles.append(dict(id=row['id'],instance=row['instance_id'],policy=row['policy_id'],context='user' if row['variant']=='baseline' else 'primary-experimental',
            **phases, process_ns=row['process_ns'],peak_rss_bytes=row['peak_rss_bytes'],
            profile_to_timing_median=row['process_ns']/timing['certified_median_ns'],residual_ns=row['residual_ns']))
    write_json(output / 'setup-components.json', profiles)
    if args.plot:
        import matplotlib
        matplotlib.use('Agg')
        matplotlib.rcParams['svg.hashsalt']='gpup-setup-v1'
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 5.8), layout='constrained')
        labels=[p['instance'].replace('gpup-development-','').replace('gpup-extension-','')+' / '+p['policy']+' / '+p['context'].replace('-experimental','') for p in profiles]
        left=[0.0]*len(profiles)
        for key, label in [('discovery','Discovery'),('driver_initialization','Driver initialization'),('context_open','Create / retain'),('context_close','Destroy / release'),('module','Module load / unload')]:
            values=[p[key]/1e6 for p in profiles];ax.barh(range(len(profiles)),values,left=left,label=label)
            left=[a+b for a,b in zip(left,values)]
        ax.set_yticks(range(len(profiles)),labels);ax.invert_yaxis();ax.set_xlabel('Exclusive host time (ms)');ax.set_title('Fresh setup components — one separate profile per cell')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.13), ncol=3, fontsize=8);fig.savefig(output/'setup-components.svg', metadata={'Date': None});plt.close(fig)
        svg = output / 'setup-components.svg'
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    ledger=ROOT/'artifacts/lp-campaign-ledgers/gpup-baseline-v1/ledger.jsonl';data=ledger.read_bytes()
    prefix=b''.join(data.splitlines(keepends=True)[:15528]);prefix_hash=hashlib.sha256(prefix).hexdigest()
    if prefix_hash != 'cb0dc57f9f92546f4cc2d93b0de3c8556d6b24517f71b7a6efaa91fa96afedb6' or file_hash(ledger)!=report['budget']['ledger_sha256']:
        raise ValueError('canonical ledger/prefix changed')
    review_path = output / 'setup-review-corrections.json'
    review = read_json(review_path) if review_path.exists() else {'files': []}
    corrections = {item['path']: item for item in review['files']}
    if len(corrections) != len(review['files']):
        raise ValueError('duplicate review correction')
    corrected = []
    checked=[]
    with tarfile.open(source/'source.tar') as archive:
        for entry in archive.getmembers():
            if entry.isfile() and (entry.name.startswith(('crates/','tools/','schemas/','benchmarks/')) or entry.name in ['Cargo.toml','Cargo.lock']):
                content=archive.extractfile(entry).read()
                if not (ROOT/entry.name).is_file() or (ROOT/entry.name).read_bytes()!=content:
                    correction = corrections.get(entry.name)
                    if (not correction or correction['measured_sha256'] != hashlib.sha256(content).hexdigest()
                            or correction['reviewed_sha256'] != file_hash(ROOT / entry.name)):
                        raise ValueError('undeclared measured source change: '+entry.name)
                    corrected.append(entry.name)
                checked.append(entry.name)
    if set(corrected) != set(corrections):
        raise ValueError('review correction does not match the measured source difference')
    original='9bf8e8d5d6f6e4fd3b2eb60ae494506ed620323e'
    history=subprocess.check_output(['git','ls-tree','-r','--name-only',original],cwd=ROOT,text=True).splitlines()
    preserved=[p for p in history if p.startswith(('cuda/','schemas/','benchmarks/','crates/optimizer-core/','crates/optimizer-lp/','crates/optimizer-experiment/','docs/decisions/'))]
    for name in preserved:
        if (ROOT/name).read_bytes()!=subprocess.check_output(['git','show',original+':'+name],cwd=ROOT): raise ValueError('historical authority changed: '+name)
    with tarfile.open(source/'baseline-source.tar') as archive:
        if 'crates/optimizer-cuda-sys/src/primary.rs' in archive.getnames(): raise ValueError('control already contained repair')
    write_json(output/'setup-source-ledger-audit.json',dict(status='passed',measured_files=len(checked),unchanged_measured_files=len(checked)-len(corrected),review_corrected_paths=corrected,review_corrections_sha256=file_hash(review_path) if review_path.exists() else None,preserved_files=len(preserved),prior_events=15528,prior_ledger_sha256=prefix_hash,
        ledger_sha256=file_hash(ledger),events=len(data.splitlines()),control_precedes_primary=True,measured_paths=checked,preserved_paths=preserved))
    cpu=[dict(path=str(p.relative_to(ROOT)),sha256=file_hash(p),**read_json(p)) for p in sorted((ROOT/'artifacts/gpup-setup-acceptance').glob('*.cpu.json'))]
    write_json(output/'setup-resources.json',dict(gpu=report['budget'],cpu_seconds=sum(r['cpu_seconds'] for r in cpu),cpu_cap_seconds=14400,cpu_receipts=cpu,
        note='Metered child CPU, including validation and independent verification; small source-edit/catalog actions are outside that meter. GPU ledger CPU reservations are separate.'))
    catalog=[]
    for name in ['gpup-setup-baseline','gpup-setup-control','gpup-setup-v1','gpup-setup-acceptance']:
        for p in sorted((ROOT/'artifacts'/name).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts: catalog.append(dict(path=str(p.relative_to(ROOT)),sha256=file_hash(p),bytes=p.stat().st_size))
    write_json(output/'setup-provenance.json',dict(schema_version=1,source_report=dict(path=str((source/'report.json').relative_to(ROOT)),sha256=file_hash(source/'report.json')),artifacts=catalog))
    print(f'Exported {len(catalog)} artifact references; {len(checked)-len(corrected)} measured files unchanged, {len(corrected)} declared corrections, {len(preserved)} historical authority files unchanged')


if __name__ == '__main__': main()
