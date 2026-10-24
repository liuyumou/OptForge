"""Explicitly authorized, preserving fixture recovery under the retained supervisor."""
import copy
import json
from pathlib import Path
import sys

import lp_cpu_admission as supervisor
import lp_tensor_expanded_authority as a

BASE = a.BASE / 'proof-recovery-v1'
JOURNAL = BASE / 'cpu-journal-v5.json'
AUTH = a.DATA / 'proof-recovery-authorization-v1.json'
MUTABLE = ['AGENTS.md', 'state/active-task.md', 'state/known-failures.md',
           'wiki/status.md', 'state/backlog.yaml', 'CHANGELOG.md']


def initialize():
    old_path = a.BASE / 'cpu-journal-final-v4.json'
    old = a.read(old_path)
    accounting = a.read(a.DATA / 'final-cpu-accounting-v1.json')
    a.checked(accounting['journal'])
    a.require(old['failed'] and old['scientific_closed'] and old['active'] is None,
              'unexpected prior journal')
    a.require(accounting['cpu_total_ns'] == 51568693453526, 'prior charge differs')
    a.preserve()
    files = [p for root in [a.BASE, a.DATA] for p in root.rglob('*')
             if p.is_file() and not p.is_relative_to(BASE)]
    files += [a.ROOT / p for p in ['tools/lp_tensor_expanded_proof.py',
               'tools/diagnostics/lp_tensor_expanded_host.cpp',
               'cuda/lp_pdhg_tensor_expanded/expanded_fast.h',
               'tools/lp_tensor_expanded_cpu.py', 'tools/lp_tensor_expanded_authority.py',
               'docs/decisions/ADR-0046-expanded-audit-window-state.md',
               'docs/plans/lp-tensor-expanded-windows.md',
               'docs/benchmarks/lp-tensor-expanded-gpup8.md',
               'docs/benchmarks/lp-tensor-expanded-final-gpup8.md']]
    a.put(BASE / 'prior-files.json', {'files': [a.ref(p) for p in sorted(set(files))]})
    for name in MUTABLE:
        p = BASE / 'prior-source' / name
        a.require(not p.exists(), 'snapshot already exists')
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((a.ROOT / name).read_bytes())
    j = copy.deepcopy(old)
    for source, target, seconds in [('authority', 'recovery_setup', 100),
                                     ('prototype', 'proof_retry', 1600)]:
        entry = j['stages'][source]
        a.require(entry['cap_cpu_ns'] - entry['charged_cpu_ns'] >= seconds * a.NS,
                  'transfer exceeds unused funds')
        entry['cap_cpu_ns'] -= seconds * a.NS
        j['stages'][target] = dict(cap_cpu_ns=seconds * a.NS, charged_cpu_ns=0)
    auth = dict(identity='gpup-tensor-expanded-proof-recovery-v1', status='accepted',
        authorization='User explicitly authorizes fixture/harness correction, one corrected proof retry, unused-budget transfers and conditional GPUP-8 continuation on 2026-10-24.',
        prior_journal=a.ref(old_path), prior_accounting=a.ref(a.DATA/'final-cpu-accounting-v1.json'),
        prior_files=a.ref(BASE/'prior-files.json'),
        transfers_cpu_seconds=[dict(source='authority', target='recovery_setup', amount=100),
                               dict(source='prototype', target='proof_retry', amount=1600)],
        proof_attempts=1, proof_work_wall_seconds=398,
        sizing='Retained compilation/worker elapsed about two seconds; 398 work-wall seconds covers both retained 120-second subprocess ceilings and independent product/projection checks.',
        additional_cpu_ns=0, cpu_ceiling_ns=old['ceiling_cpu_ns'],
        historical_failed_proof_charge_ns=5600*a.NS,
        unchanged_later_stages=['implementation','native','acceptance','profiles','timings','reporting','margin'],
        scientific_criteria_changed=False, passed_checks_rerun=False, passed_profiles_rerun=False,
        supervisor=a.ref(a.ROOT/'tools/lp_cpu_admission.py'), ledger=a.ref(a.LEDGER),
        gpu_allocation_changed=False, automatic_numerical_retry=False)
    a.put(AUTH, auth)
    j.update(identity='gpup-tensor-expanded-proof-recovery-journal-v5', failed=False,
             scientific_closed=False, delivery_complete=False, delivery_only=False,
             authorization=a.ref(AUTH), prior_closed_journal=a.ref(old_path))
    j.pop('closed_reason', None)
    j['stages']['recovery_setup']['charged_cpu_ns'] = 16*a.NS
    j['runs'].append(dict(stage='recovery_setup', charged_cpu_ns=16*a.NS,
        status='conservative_authorization_bookkeeping', output=str(AUTH)))
    a.require(j['prior_cpu_ns'] + sum(v['cap_cpu_ns'] for v in j['stages'].values()) <= j['ceiling_cpu_ns'],
              'allocation exceeds ceiling')
    a.put(JOURNAL, j)
    status = '''## GPUP-8 authorized fixture correction and one proof retry (2026-10-24)

The user authorizes fixture/harness fixes, one corrected proof attempt and
conditional continuation from unused funds. This supersedes the earlier proof
stop only for this recovery. Transfer 100 unused authority CPU seconds to setup
and 1600 unused prototype seconds to the corrected proof reservation; add no
resources. Retain the full 5600-second failed proof charge and all original
sources, corpus, reports and journals. CPU ceiling remains 77640; GPU caps and
every completion criterion remain unchanged.

Active journal: artifacts/gpup-tensor-expanded-v1/proof-recovery-v1/cpu-journal-v5.json.
Authority: docs/benchmarks/data/tensor-expanded/proof-recovery-authorization-v1.json.
Implement versioned generator/harness adapters, canonical-input preflight and
indexed diagnostics. Reuse the source-bound 12 authority and 16 prototype passes;
rerun no passed checks or historical profiles. After the corrected proof passes,
continue the accepted ordered gates. No supervisor/bootstrap/host/container
change. A numerical or resource failure retains its charge and closes later
scientific stages. GPUP-8 remains incomplete until all criteria pass; GPUP-9 stays
gated. Expected writes: correction adapters, focused validation, new receipts,
accounting, and conditional candidate implementation under ADR-0046.

'''
    for name in ['AGENTS.md', 'state/active-task.md']:
        p = a.ROOT/name
        first, rest = p.read_text().split('\n', 1)
        p.write_text(first+'\n\n'+status+rest.lstrip('\n'))
    print('Authorized preserving correction; 1700 unused CPU seconds transferred; no new budget.')


def preservation():
    auth = a.read(AUTH)
    a.checked(auth['prior_journal'])
    a.checked(auth['prior_accounting'])
    a.checked(auth['supervisor'])
    for item in a.read(a.checked(auth['prior_files']))['files']:
        a.checked(item)
    a.preserve()
    reused = []
    for name in ['authority', 'prototype']:
        path = a.BASE/(name+'-resource-v1.json')
        r = a.read(path)
        a.require(r['status'] == 'passed', 'retained check did not pass')
        for source in r['request']['command_sources']:
            p = Path(source['path'])
            a.require(a.ref(p)['sha256'] == source['sha256'], 'reused check dependency changed')
        reused.append(a.ref(path))
    return reused


def run_stage(stage):
    a.require(stage in ['recovery_setup', 'proof_retry'], 'invalid recovery stage')
    preservation()
    j = a.read(JOURNAL)
    if stage == 'proof_retry':
        setup = a.read(BASE/'recovery_setup-resource-v1.json')
        a.require(setup['status'] == 'passed', 'fixture preflight did not pass')
        a.checked(a.read(BASE/'preflight-v2.json')['binary'])
    reserve = j['stages'][stage]['cap_cpu_ns'] - j['stages'][stage]['charged_cpu_ns']
    a.stage_admission(j, stage, reserve)
    out = BASE/(stage+'-resource-v1.json')
    a.require(not out.exists(), 'duplicate attempt')
    j['stage_attempts'][stage] = dict(output=str(out.relative_to(a.ROOT)), reserved_cpu_ns=reserve)
    supervisor.atomic_json(JOURNAL, j)
    sources = ['tools/lp_tensor_expanded_recovery.py', 'tools/lp_tensor_expanded_proof_v2.py',
        'tools/diagnostics/lp_tensor_expanded_host_v2.cpp', 'tools/lp_tensor_expanded_proof.py',
        'tools/lp_tensor_expanded_authority.py', 'tools/lp_tensor_expanded_cpu.py',
        'tools/lp_expansion_oracle.py', 'tools/lp_expansion_candidate.py',
        'tools/diagnostics/lp_state_compact_probe.cu', 'tools/diagnostics/lp_state_integer_probe.cu',
        'cuda/lp_pdhg_tensor_expanded/expanded_fast.h']
    command = [sys.executable, str(a.ROOT/'tools/lp_tensor_expanded_proof_v2.py'),
               'preflight' if stage == 'recovery_setup' else 'proof']
    result = supervisor.run(dict(stage=stage, reserve_cpu_seconds=reserve/a.NS,
        output=str(out), log=str(out)+'.log', journal=str(JOURNAL),
        lock=str(a.ROOT/'artifacts/lp-cpu-admission.lock'), slots=4,
        declared_memory_bytes=4<<30, rss_stop_bytes=6<<30, address_space_bytes=0,
        sources=[str(a.ROOT/p) for p in sources], bootstrap=False, show_log=True,
        max_gap_ns=100_000_000, command=command))
    if result['status'] != 'passed':
        j = a.read(JOURNAL)
        j['scientific_closed'] = True
        supervisor.atomic_json(JOURNAL, j)
    print(json.dumps(dict(stage=stage, status=result['status'], charged_cpu_ns=result['charged_cpu_ns'])))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    if sys.argv[1] == 'initialize':
        initialize()
    else:
        raise SystemExit(run_stage(sys.argv[1]))
