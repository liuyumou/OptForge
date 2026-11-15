"""Prospective grouped splits, balanced schedules and selection without holdout access."""
import argparse
import hashlib
import math
import random
import statistics
from lp_gpup9_common import (BASE, BINARY, IMAGE, SERIAL, ROOT, FAMILIES, SETTINGS,
                            CPU_CAPS, GPU_CAPS, configs, load, put, ref, checked, require)

STAGES = dict(screening=(3, 4, 400), validation=(10, 32, 360), holdout=(16, 32, 480))


def descriptors(partition):
    seed = dict(admission=340078, screening=440078, validation=540078, holdout=640078)[partition]
    return [dict(id=f'{partition}-{family}', family=family, partition=partition,
                 seed=seed+i, size=int(family.rsplit('-', 1)[1]),
                 generator='gpup9-diagonal-v2', license='MIT')
            for i, family in enumerate(FAMILIES)]


def source_bindings():
    # All tracked implementation dependencies, including imported tooling and Rust.
    import subprocess
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    paths = [ROOT/p for p in paths if p and (p.startswith(('tools/', 'research/', 'crates/'))
             or p in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'])]
    paths += list((ROOT/'tools').glob('lp_gpup9*.py'))
    paths += list((ROOT/'schemas').glob('lp-gpup9*.json'))
    paths += [ROOT/'docs/specifications/SPEC-0044-gpup9-controlled-study.md',
              ROOT/'docs/decisions/ADR-0078-gpup9-controlled-study.md',
              ROOT/'tests/integration/test_lp_gpup9.py']
    return [ref(p) for p in sorted(set(paths))]


def design():
    return dict(schema_version=1, kind='gpup9-design', study_id='gpup9-v2', configurations=configs(),
                partitions={p:descriptors(p) for p in ['admission', *STAGES]},
                stages={p:dict(blocks=b, count=n, seconds=s) for p,(b,n,s) in STAGES.items()},
                settings=SETTINGS, alpha=.05, endpoints=24, value_ms=10,
                cpu_caps=CPU_CAPS, gpu_caps=GPU_CAPS, source=source_bindings(),
                binary=ref(BINARY), image=ref(IMAGE), serial=ref(SERIAL),
                target='x86-64-v4', default_change=False, no_retry=True)


def verify_design(d):
    expected=design()
    require(set(d)==set(expected), 'design schema fields')
    require({k:v for k,v in d.items() if k!='source'}=={k:v for k,v in expected.items() if k!='source'}, 'frozen protocol changed')
    if (BASE/'implementation-v5.json').exists():
        implementation=load(BASE/'implementation-v5.json')
        require(implementation['design']==ref(BASE/'design-v2.json'),'implementation protocol identity')
        require(implementation['source']==expected['source'],'implementation source identity changed')
    else:require(d['source']==expected['source'],'initial source identity changed')
    groups=[g for gs in d['partitions'].values() for g in gs]
    require(len({g['id'] for g in groups})==len(groups), 'duplicate group')
    require(len({g['seed'] for g in groups})==len(groups), 'seed/split leakage')
    return d


def implementation():
    require(not list(BASE.glob('*-freeze.json')),'cannot revise implementation after scientific freeze')
    put(BASE/'implementation-v5.json',dict(schema_version=1,identity='gpup9-implementation-v5',
        design=ref(BASE/'design-v2.json'),source=source_bindings(),
        previous_sources=ref(BASE/'sources/design-v1/manifest.json'),
        reason='Remove redundant inner admission_open check that rejected the supervised metadata job itself. The outer budget wrapper still refuses every prior unsettled reservation before starting a job. Whole-stage reservation checks, generator-v2, solver/image, criteria and allocation are unchanged. No scientific cohort previously frozen.',
        previous_implementation=ref(BASE/'implementation-v4.json'),
        retained_failures=[ref(BASE/'resources'/name) for name in ['pilot-v1.settlement.json','models-screening.settlement.json','freeze-screening.settlement.json']]))


def schedule(stage, selected):
    blocks, count, _ = STAGES[stage]
    rng=random.Random(dict(screening=440079, validation=540079, holdout=640079)[stage])
    keys=sorted(selected)
    endpoints=['prepared','cold'] if stage=='holdout' else ['prepared']
    pairs=[(g,e) for g in descriptors(stage) for e in endpoints]
    orders={g['id']+'-'+e:rng.sample(keys,len(keys)) for g,e in pairs}
    offsets={g['id']+'-'+e:rng.sample(list(range(blocks)),blocks) for g,e in pairs}
    result=[]
    for block in range(blocks):
        shuffled=pairs.copy();rng.shuffle(shuffled)
        for group,endpoint in shuffled:
            identity=group['id']+'-'+endpoint
            order=orders[identity]
            offset=offsets[identity][block]%len(keys)
            order=order[offset:]+order[:offset]
            for position,config in enumerate(order):
                result.append(dict(id=f'b{block:02d}-{identity}-{config}', block=block,
                    group=group['id'], family=group['family'], endpoint=endpoint,
                    config=config, position=position, count=1 if endpoint=='cold' else count))
    return result


def select(stage, rows, expected, configuration_map):
    require(stage in ['screening','validation'], 'holdout cannot select or tune')
    require(len(rows)==len(expected), 'selection requires complete planned coverage')
    require({r['id'] for r in rows}=={c['id'] for c in expected}, 'selection roster differs')
    roster={c['id']:c for c in expected}
    for row in rows:
        require(all(row[k]==v for k,v in roster[row['id']].items()), 'selection cell mismatch')
        require(row['complete_session_ns']>0 and len(row['records'])==row['count'], 'incomplete selection row')
    families=sorted({r['family'] for r in rows})
    # Geometric means of group medians; the common reference cancels in rankings.
    scores={}
    for key,cfg in configuration_map.items():
        selected=[r for r in rows if r['config']==key]
        require(selected, 'configuration missing')
        failed=sum(not all(x['certified'] for x in r['records']) for r in selected)
        medians=[statistics.median(r['complete_session_ns'] for r in selected if r['family']==f)
                 for f in families]
        scores[key]=dict(failed_sessions=failed, geometric_mean_ns=math.exp(
            statistics.mean(math.log(v) for v in medians)))
    groups=[(lane,scale) for lane in ['native','fp4x2'] for scale in [False,True]] if stage=='screening' else [(lane,None) for lane in ['native','fp4x2']]
    winners=[]
    for lane,scale in groups:
        eligible=[k for k,c in configuration_map.items() if c['lane']==lane and
                  (scale is None or c['equilibrate']==scale)]
        winners.append(min(eligible,key=lambda k:(scores[k]['failed_sessions'],scores[k]['geometric_mean_ns'],k)))
    return dict(selected={k:configuration_map[k] for k in sorted(winners)}, scores=scores,
                selection_partition=stage, holdout_accessed=False,
                full_coverage=all(scores[k]['failed_sessions']==0 for k in winners))


def projected_session(row, count):
    require(row['records'] and type(count) is int and count>0,'invalid pilot projection')
    fixed=row['complete_session_ns']-sum(r['complete_ns'] for r in row['records'])
    require(fixed>=row['setup_ns']+row['teardown_ns'],'invalid pilot lifecycle')
    return (fixed+max(r['complete_ns'] for r in row['records'])*count)/1e9


def stage_budget_fits(stage,cpu,gpu):
    blocks,_,seconds=STAGES[stage]
    require(cpu[stage]+blocks*4*seconds*10**9<=CPU_CAPS[stage]*10**9,'whole stage CPU cannot fit')
    require(gpu[stage]+blocks*seconds*10**9<=GPU_CAPS[stage]*10**9,'whole stage GPU cannot fit')


def freeze(stage):
    d=verify_design(load(BASE/'design-v2.json'))
    if stage=='screening':
        chosen=d['configurations']
        admissions=[ref(BASE/'admission-v2.json'),ref(BASE/'serial-admission-v2/result.json')]
        require(load(BASE/'admission-v2.json')['status']=='passed','current admission required')
        require(load(BASE/'resources/projection-v1.settlement.json')['status']=='passed','projection contracts required')
        admissions.append(ref(BASE/'resources/projection-v1.settlement.json'))
        require(load(BASE/'resources/freeze-contracts-v1.settlement.json')['status']=='passed','freeze contracts required')
        admissions.append(ref(BASE/'resources/freeze-contracts-v1.settlement.json'))
    else:
        predecessor='screening' if stage=='validation' else 'validation'
        selection=load(BASE/f'{predecessor}-selection.json')
        require(selection['selection_partition']==predecessor and not selection['holdout_accessed'],'selection provenance')
        from lp_gpup9_analysis import rows
        previous,observed,missing=rows(predecessor)
        require(not missing,'incomplete predecessor cannot release next partition')
        reproduced=select(predecessor,observed,previous['cells'],previous['configurations'])
        require(all(selection[k]==v for k,v in reproduced.items()),'selection does not reproduce')
        require(selection['freeze']==ref(BASE/f'{predecessor}-freeze.json'),'selection freeze changed')
        require(selection['sessions']==[ref(BASE/predecessor/f"b{r['block']:02d}"/(r['id']+'.session.json')) for r in observed],'selection corpus changed')
        chosen=selection['selected'];admissions=[ref(BASE/f'{predecessor}-selection.json')]
    require(all(k in d['configurations'] and v==d['configurations'][k] for k,v in chosen.items()),'unknown or altered finalist')
    # The outer budget wrapper checks admission before reserving this metadata
    # job. Calling admission_open here would reject our own live reservation.
    from lp_gpup9_budget import accounting
    cpu,gpu=accounting()
    blocks,_,seconds=STAGES[stage]
    stage_budget_fits(stage,cpu,gpu)
    pilot=load(BASE/'pilot-v3/result.json')['sessions']
    # Pilot includes full 32-request costs for every family and both lanes.
    estimates={(r['family'],configs()[r['config']]['lane']):r for r in pilot}
    planned=schedule(stage,chosen)
    projected=max(sum(projected_session(estimates[c['family'],chosen[c['config']]['lane']],c['count'])
                      for c in planned if c['block']==b) for b in range(blocks))
    require(projected*1.5<seconds,'admitted cost cannot fit whole block')
    manifest=ref(BASE/'models-v2'/stage/'manifest.json') if stage!='holdout' else None
    put(BASE/f'{stage}-freeze.json',dict(schema_version=1,kind='gpup9-freeze',stage=stage,
        design=ref(BASE/'design-v2.json'),implementation=ref(BASE/'implementation-v5.json'),configurations=chosen,cells=planned,blocks=blocks,
        seconds=seconds,models=manifest,admissions=admissions,projected_block_seconds=projected,
        projection_method='full observed non-request cost plus maximum observed request cost times declared count; 1.5 admission margin; cold conservatively retains four-model setup'))


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['design','implementation','freeze']);p.add_argument('--stage',choices=STAGES);a=p.parse_args()
    if a.command=='design':put(BASE/'design-v2.json',design())
    elif a.command=='implementation':implementation()
    else:freeze(a.stage)

if __name__=='__main__':main()
