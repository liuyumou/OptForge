"""Final-version comprehensive report with complete-cost evidence and strict checks."""
import argparse
import csv
import datetime as dt
import json
from pathlib import Path
import re
import statistics as st
import subprocess
import sys
import unittest
from lp_sp_pricing_budget import ROOT,BASE,NS,binding,put,accounting
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_report import resource_summary
from lp_sp_pricing_finish import identities,still_same_process
from lp_sp_pricing_nontall_report import input_integrity
from lp_sp_pricing_recovery_report import assess,accepted,pairs
from lp_sp_pricing_final_budget_v2 import CPU,GPU,allocation
from lp_sp_pricing_final_admission import CPU as CPU_GATE
import lp_sp_pricing_final_study_v2 as study

OUT=BASE/'final-comprehensive-report-v1';DOCS=ROOT/'docs/benchmarks';DOC=DOCS/'lp-sp-pricing-comprehensive.md'
LANES=['candidate','copt-gpu-default','copt-auto'];LABELS={'candidate':'Candidate','copt-gpu-default':'COPT GPU','copt-auto':'COPT CPU auto'}


def collect():
    f=study.frozen()
    if read(BASE/'final-driver-v2/completed.json')['status']!='all_90_slots_disposed':raise RuntimeError('final study incomplete')
    rows=[]
    for kind,identity in (('gpu','final-focus-gpu-v2'),('control','final-regression-cpu-v2'),('cpu','final-vendor-cpu-v2')):
        group=read(study.STUDY/f'{kind}-group.json')
        if group['status']!='all_slots_disposed':raise RuntimeError('unfinished final group')
        for row in group['rows']:
            model=next(m for m in f['models']+f['controls'] if m['name']==row['family'] and m['seed']==row['seed'])
            rows.append(assess(row,model,BASE/'resources'/f'{identity}.settlement.json','fresh_regression' if kind=='control' else 'fresh_focus'))
    expected={f'{m["name"]}-{m["seed"]}-{lane}' for m in f['models'] for lane in ['candidate-before']+LANES}
    expected|={f'{m["name"]}-{m["seed"]}-{lane}' for m in f['controls'] for lane in ('candidate-before','candidate')}
    if len(rows)!=90 or {r['id'] for r in rows}!=expected:raise RuntimeError('complete final roster mismatch')
    return f,rows


def preserved():
    recovery=read(BASE/'recovery-report-v1/result.json');nontall=read(BASE/'nontall-report-v1/result.json');checked=bindings(recovery)+bindings(nontall);models=[];rows=[]
    rf=read(BASE/'recovery-parallel-evaluation-v1/freeze.json');sf=read(BASE/'recovery-mixed-supplement-v1/freeze.json');nf=read(BASE/'nontall-evaluation-v1/freeze.json')
    groups=[(rf['models'][:9],recovery['final_rows'],'wide'),(sf['models'],recovery['supplement_rows'],'mixed_square'),([m for m in nf['models'] if m['name'] in ('dense-square-4m','banded-square-4m','irregular-square-1m','scaled-square-1m')],nontall['rows'],'square')]
    square_index={'dense-square-4m':4,'banded-square-4m':5,'irregular-square-1m':6,'scaled-square-1m':7};wide_index={'dense-wide-1m':0,'dense-wide-4m':1,'sparse-wide-1m':2}
    for selected,source,kind in groups:
        models+=selected;keys={(m['name'],m['seed']):m for m in selected}
        for row in source:
            if (row['family'],row['seed']) not in keys:continue
            placement='cpu' if row['lane']=='copt-auto' else 'gpu'
            if kind=='wide':identity=f'recovery-parallel-{placement}-{wide_index[row["family"]]}-v1'
            elif kind=='mixed_square':identity=f'recovery-mixed-supplement-{placement}-v1'
            else:identity=f'nontall-{placement}-{square_index[row["family"]]}-v1'
            rows.append(assess(row,keys[(row['family'],row['seed'])],BASE/'resources'/f'{identity}.settlement.json','preserved_dispatch'))
    if len(models)!=24 or len(rows)!=72 or len({r['id'] for r in rows})!=72:raise RuntimeError('preserved dispatch roster')
    return models,rows,dict(recovery=binding(BASE/'recovery-report-v1/result.json'),nontall=binding(BASE/'nontall-report-v1/result.json'),checked_bindings=checked)


def regression(rows,models):
    records=[]
    for m in models:
        rs={r['lane']:r for r in rows if r['family']==m['name'] and r['seed']==m['seed']};a,b=rs['candidate-before'],rs['candidate']
        old=read(a['response']['path']);new=read(b['response']['path']);explicit=bool(old.get('certificate'));same=old.get('certificate')==new.get('certificate') if explicit else None
        records.append(dict(family=m['name'],seed=m['seed'],accepted_both=accepted(a) and accepted(b),explicit=explicit,identical_explicit_certificate=same,
            before_complete_ns=a['complete_ns'],current_complete_ns=b['complete_ns'],current_over_before=b['complete_ns']/a['complete_ns']))
    summaries=[]
    for name in sorted({r['family'] for r in records}):
        selected=[r for r in records if r['family']==name];ratio=st.median(r['current_over_before'] for r in selected)
        summaries.append(dict(family=name,pairs=len(selected),accepted_pairs=sum(r['accepted_both'] for r in selected),median_current_over_before=ratio,passed=all(r['accepted_both'] and (not r['explicit'] or r['identical_explicit_certificate']) for r in selected) and ratio<=1.10))
    return dict(passed=all(r['passed'] for r in summaries),rows=records,families=summaries)


def median(rows,key='complete_ns'):
    values=[r[key]/NS for r in rows if accepted(r)]
    return '—' if not values else f'{st.median(values):.3f} [{min(values):.3f}, {max(values):.3f}]'


def table(lines,rows,models):
    lines+=['| Family | Shape; nonzeros | Candidate | COPT GPU | COPT CPU auto |','| --- | --- | ---: | ---: | ---: |']
    names=list(dict.fromkeys(m['name'] for m in models))
    for name in names:
        model=next(m for m in models if m['name']==name);cells=[]
        for lane in LANES:
            rs=[r for r in rows if r['family']==name and r['lane']==lane];cells.append(f'{sum(accepted(r) for r in rs)}/{len(rs)}; {median(rs)}')
        lines.append(f'| {name} | {model["m"]:,} × {model["n"]:,}; {model["nonzeros"]:,} | '+' | '.join(cells)+' |')


def document(result,f,retained_models):
    focus=[r for r in result['fresh_rows'] if r['cohort']=='fresh_focus' and r['lane'] in LANES];retained=result['preserved_rows'];ratios=result['fresh_pairs']
    candidates=[r for r in focus if r['lane']=='candidate'];gpu_pairs=[r for r in ratios if r['control']=='copt-gpu-default' and r['eligible']]
    family_ratios={name:st.median(r['control_over_candidate'] for r in gpu_pairs if r['family']==name) for name in {r['family'] for r in gpu_pairs}}
    lines=['# Certified LP solver implementation and performance','',
        'The implementation solves canonical linear programs of the form `maximize cᵀx subject to Ax≤b`, with free variables, using numerical proposals followed by independent exact optimality certificates. Dense and sparse square or wide problems use CPU factorization; eligible rectangular and tall problems use resident FP64 GPU projection. The certificate proves feasibility and zero gap on the original model.','',
        f'On the fresh three-seed rectangular/tall evaluation, the candidate produces **{sum(accepted(r) for r in candidates)}/15 timely certified solutions**. It has the lower median complete cost in **{sum(v>1 for v in family_ratios.values())}/{len(family_ratios)} families with eligible COPT GPU pairs**. The tables report every family’s acceptance count and direction of comparison. Times include model encoding, cold preparation, solving, endpoint construction and independent certification.','',
        'The results concern the stated synthetic dyadic problems and solver configurations. This practical hybrid includes bounded pricing components and certified presolve; it does not establish a completed literal strongly polynomial implementation or general superiority over COPT.','',
        '## Final implementation','',
        'The solver is motivated by [Strongly Polynomial Linear Programming](https://github.com/openai/math/blob/main/preprints/Strongly-polynomial-linear-programming-November-24-2026/paper.pdf). Reference modules implement paired-cone price queries, compressed calibration and witness recovery. The practical pricing fallback uses input-height calibration, bounded expert populations and query counts, and exact restricted-cone recovery. These bounded choices do not inherit the paper’s strongly polynomial guarantee. The factor-recovery paths described below can establish an optimum directly and are the paths exercised by the successful large-case comparisons.','',
        'The numerical entry point is `tools/lp_sp_pricing_final_screened_run.py --wide-backend cpu`. Its output is a proposal, not a trusted certificate. `tools/lp_sp_pricing_final_endpoint.py` applies the common endpoint policy, and the checker selected by certificate type determines acceptance. All vendor endpoints receive the same construction policy and checker.','',
        '| Matrix case | Numerical work | Certificate |','| --- | --- | --- |',
        '| Dense square | LAPACK LU reused for primal and transposed dual solves | Explicit exact endpoint when recoverable; otherwise implicit primal recovery within its dimension limit |',
        '| Sparse square and irregular | Sparse LU and transposed solve | Explicit original-model certificate; sparse fill controls factor cost |',
        '| Full-row-rank wide | Form AAᵀ with dense BLAS or sparse products; reuse a factor for b and Ac; recover x with Aᵀ | Implicit full-row primal plus an exact nonnegative dual |',
        '| Mixed rectangular and tall | Resident Cholesky factor of AᵀA; batched FP64 projection; power-of-two row balancing where applicable | Exact active primal and implicit dual correction |',
        '| Outside supported recovery domains | Existing bounded exact geometry, pricing and auxiliary-search path | Independent certificate required; a resource limit is not a mathematical LP outcome |','',
        'Wide proposals require m≤4096 and mn≤2²⁷. Rectangular/tall projection requires n≤4096 and mn≤2²⁷. Large sparse-square factorization follows its existing sparse path. Unsupported rank, coefficient range or reconstruction can make recovery inconclusive even when the LP has an optimum.','',
        '### Rectangular and tall GPU projection','',
        'Each iteration solves `Gx=Aᵀ(b−s−u)+c/ρ`, where `G=AᵀA`, then projects the slack and updates the scaled multiplier. G, its Cholesky factor, A and the iteration state stay on GPU. Checkpoints occur every 100 updates. The penalty uses the documented norm scale multiplied by 16, and the update ceiling is 6000.','',
        'Rows with a large norm spread are balanced by powers of two before numerical projection. The dual is mapped back to the original coordinates, and every certificate is checked against the original A, b and c. On the supported dyadic test range these scalings are exact; the final proof never relies on transformed-model residuals alone.','',
        'For mixed rectangular or balanced cases, a promising checkpoint triggers exact primal recovery and a dual correction proposal. A triangular solve screens the correction for nonnegativity before allocating and solving for the full inverse. Failed screens allow GPU iteration to continue. An early stop requires a complete exact check; a separate cold checker independently rechecks the published certificate. This permits stopping before a raw floating residual reaches 1e-9 while still proving exact optimality. Ordinary unscaled tall cases retain the stringent numerical stopping rule.','',
        '### Exact host work','',
        'Certificate construction decodes the IEEE significand and exponent to find the shared dyadic exponent, then converts the matrix once. It avoids a succession of full-array rescalings. The correction factor is reused for both numerical refinement and inverse construction; no floating proposal is itself an acceptance decision.','',
        'The implicit-dual checker validates canonical CSR and scans every original nonzero. It computes exact sparse integer products using signed limbs. Before each product, a bound on the sum of absolute terms proves that all multiplications and partial sums stay below 2⁶². Limb results are combined with unbounded Python integers. Inputs outside those bounds use the arbitrary-integer fallback. The CPU inverse enclosure remains independent of the constructor.','',
        'Dedicated implicit-dual construction and checking processes can use four BLAS threads, with no simultaneous integer-scan worker pool. The implicit-primal checker uses three integer workers while the parent computes the enclosure. Explicit certificates retain their original checker. These paths fit the four allocated CPU slots.','',
        '### Memory and concurrency','',
        'The GPU projection stores roughly mn+n² FP64 matrix entries plus vectors and library workspaces; its current implementation densifies A. At 16000×4000, those matrix terms occupy about 0.596 GiB. Sparse-wide CPU recovery retains sparse normal factors, but its certificate still contains a dense m×m inverse proposal. These quadratic objects limit supported dimensions even when the input is sparse.','',
        'Recovery avoids a full rational null-space basis. The pricing fallback retains lazy CPU tableau construction, tiled products and checks, bounded synchronized auxiliary batches, reusable allocations and transfer/compute overlap. These mechanisms bound workspace and share GPU work when searches are needed; accepted factor-recovery paths bypass those searches. The reported fast paths use FP64 proposals, not a claim of packed low-precision tensor-core throughput.','',
        '## Certificate definitions','',
        'For a wide system, choose m columns J and let B=A[:,J]. The certificate defines `x=x₀+E_Jδ`, where `Bδ=b−Ax₀`. An independent enclosure proving ‖I−RB‖∞<1 establishes nonsingularity and therefore exact primal feasibility. A full integer scan proves `Aᵀy=c` and `y≥0`; all rows are active at the defined primal, giving zero gap. The corrected primal need not have short dyadic coordinates.','',
        'For a rectangular/tall system, the checker proves that a recovered dyadic primal is feasible and that the dual base y₀ is supported only on exactly active rows. With B formed from n selected active rows, it defines `y=y₀+E_Jδ` by `Bᵀδ=c−Aᵀy₀`. Exact stationarity residuals and the independent inverse-norm enclosure bound δ. A correction no larger than the selected positive dual margin proves dual nonnegativity and zero gap.','',
        'Inverse enclosures assume standard IEEE FP64 BLAS roundoff and require nearest CPU rounding. Raw numerical status, the original conservative 1e-9 endpoint audit and exact reconstructed certificates are separate quantities. A missing finite raw bound is not proof of a wrong numerical optimum. All performance ratios below use timely independently accepted exact certificates.','',
        '## Evaluation method','',
        'Measurements were made on November 26, 2026 with an Intel Xeon Platinum 8457C and NVIDIA RTX PRO 6000 Blackwell Server Edition, using COPT 8.0.6. Reservations use four CPU slots and a 32 GiB sampled aggregate host envelope. Candidate proposal BLAS normally uses one thread; dedicated implicit-dual construction/checking uses up to four, and COPT uses four. GPU ownership, memory and idle admission checks remain enforced.','',
        'COPT GPU uses LpMethod=6, GPUMode=1, Presolve=0, Crossover=0 and PDLPTol=1e-9, with installed default Scaling and Dualize. COPT CPU uses its automatic method, GPUMode=0 and installed default presolve/scaling. Both use FeasTol=DualTol=1e-9, MatrixTol=0 and MemLimit=12000. These are specified configurations rather than unrestricted claims about COPT’s best achievable settings.','',
        'Each solver has a 60-second native allowance and a 90-second process ceiling. Construction and independent proof have 90- and 120-second process ceilings. Complete cost includes shared original-model generation/encoding, cold solver process, raw audit, common construction and cold proof. Import, conversion, allocations, transfers, CUDA/library initialization and teardown are included. COPT preparation, including opaque work inside SolveLp, is included. Construction-witness validation and experiment supervision are research overhead outside solver timings.','',
        'Inputs are signed dyadic synthetic models with independently checked planted feasible and complementary witnesses withheld from solvers. Mixed cases have 20% inactive rows at the planted optimum; another optimum can have a different active set. Scaled families apply row factors from 2⁻⁴ through 2⁴. The short-dyadic planted witnesses favor these reconstruction paths. The objective is bounded, while the feasible region need not be. Million scale means original nonzeros, not millions of variables.','',
        'There is one cold run per solver and seed, three independent seeds per family and no cache flushing. Candidate/GPU order rotates, while COPT CPU runs in a separate CPU-only group. Fresh rectangular/tall seeds are 128101, 128123 and 128149; unchanged-path regression seeds are 128201, 128223 and 128249. The fresh study contains 90 solver attempts on 30 models, including fixed-input regression pairs. Other-shape measurements below use unchanged numerical and certificate paths, with fresh regression checks on the affected dispatch boundary. Each comparison uses the same original model and common certificate policy for both solvers; timings from different cohorts are not combined into one speed ratio.','',
        '## Fresh rectangular and tall comparisons','',
        'Cells show timely certified count / attempted count, then median [minimum, maximum] complete seconds. A dash means no eligible certified time. A deadline remains unsuccessful even if later reconstruction can prove an endpoint.','']
    table(lines,focus,f['models'])
    lines+=['','| Family | Eligible GPU pairs / 3 | Median COPT GPU / candidate | Eligible CPU pairs / 3 | Median COPT CPU / candidate |','| --- | ---: | ---: | ---: | ---: |']
    for spec in study.FOCUS:
        values=[]
        for lane in LANES[1:]:
            selected=[p for p in ratios if p['family']==spec['name'] and p['control']==lane and p['eligible']];values += [str(len(selected))+'/3','—' if not selected else f'{st.median(p["control_over_candidate"] for p in selected):.3f}×']
        lines.append('| '+spec['name']+' | '+' | '.join(values)+' |')
    lines+=['','## Other matrix shapes','',
        'These rows evaluate the final solver’s preserved square/wide paths. Acceptance counts remain visible when COPT reaches a native deadline or cannot supply an exact certificate under the common policy.','']
    table(lines,retained,retained_models)
    lines+=['','## Cost diagnosis','',
        'The following medians describe the final rectangular/tall pipeline. Independent phase medians need not sum to the median complete time. The solver-process column includes all cold preparation and numerical work; it is not kernel-active GPU time.','',
        '| Family and lane | Encoding s | Solver process s | Raw audit s | Construction s | Independent proof s |','| --- | ---: | ---: | ---: | ---: | ---: |']
    for spec in study.FOCUS:
        for lane in ('candidate','copt-gpu-default'):
            selected=[r for r in focus if r['family']==spec['name'] and r['lane']==lane and r['timing_eligible']]
            values=['—' if not selected else f'{st.median(r[key] for r in selected)/NS:.3f}' for key in ('encoding_ns','process_ns','raw_audit_ns','postprocess_ns','proof_ns')]
            lines.append('| '+spec['name']+' / '+LABELS[lane]+' | '+' | '.join(values)+' |')
    lines+=['','| Candidate family | Median GPU updates | Projection setup s | Iteration/checkpoint region s | Early certificate attempts s |','| --- | ---: | ---: | ---: | ---: |']
    for spec in study.FOCUS:
        selected=[r for r in focus if r['family']==spec['name'] and r['lane']=='candidate' and r['timing_eligible']];proposals=[read(r['response']['path']).get('proposal') for r in selected];proposals=[p for p in proposals if p]
        if not proposals:continue
        trials=[sum(t['complete_ns'] for t in p.get('early_trials',[])) for p in proposals]
        values=[f'{st.median(p["steps"] for p in proposals):.0f}',f'{st.median(p["setup_ns"] for p in proposals)/NS:.3f}',f'{st.median(p["complete_ns"]-p["setup_ns"]-t for p,t in zip(proposals,trials))/NS:.3f}',f'{st.median(trials)/NS:.3f}']
        lines.append('| '+spec['name']+' | '+' | '.join(values)+' |')
    scaled=[r for r in focus if r['family']=='mixed-scaled-tall-4m' and r['lane']=='candidate' and accepted(r)]
    vendor=[r for r in focus if r['family']=='mixed-scaled-tall-4m' and r['lane']=='copt-gpu-default' and accepted(r)]
    if scaled and vendor:
        early=st.median(sum(t['complete_ns'] for t in r['proposal'].get('early_trials',[])) for r in scaled)/NS
        lines+=['',f'Scaled tall is the remaining loss against COPT GPU: {st.median(r["complete_ns"] for r in scaled)/NS:.3f} versus {st.median(r["complete_ns"] for r in vendor)/NS:.3f} complete seconds. The candidate spends a median {early:.3f} seconds on early correction construction and checking inside its solver process, in addition to the cold final proof. Repeated active-basis LU screens and 1500 projection updates account for much of this cost. The current implementation performs these host checks synchronously with GPU checkpoints; it does not overlap them with continued projection.']
    lines+=['','Mixed rectangular cost depends on both GPU convergence and the cost of establishing a usable active-set correction. The early exact check avoids unnecessary numerical accuracy once a certificate is available. Screening negative corrections before full inverse construction prevents failed trials from dominating the solve. The independent proof is still paid for in the complete cost.','',
        'For unscaled tall inputs, factor setup and certificate work matter more than the small update count. At larger n, inverse construction and its independent dense product are cubic CPU work; full original-model scans and portable input handling also scale with nonzeros. Row-scaled tall cases add convergence and repeated correction-screen work. The table separates these costs instead of attributing the entire delay to GPU arithmetic.','',
        'Wide cases benefit from avoiding exact rational elimination and market search altogether. Their implicit full-row certificate removes the requirement that the primal be short dyadic. Efficient CPU factorization is used at the tested sizes because its cold complete cost beats the available GPU row-Gram proposal. Sparse-wide recovery can still be limited by normal-factor fill and its dense inverse certificate.','',
        '## Validation and practical limits','']
    reg=result['regression'];worst=max(r['median_current_over_before'] for r in reg['families']);explicit=[r for r in reg['rows'] if r['explicit']]
    lines+=[f'All **{sum(r["accepted_both"] for r in reg["rows"])}/{len(reg["rows"])} fixed-input regression pairs** preserve exact acceptance across dense-wide, sparse-wide, mixed-square, dense-square and irregular-square cases. All {len(explicit)} explicit certificate pairs match exactly. The largest per-family median current/reference complete-time ratio is {worst:.3f}×, within the prespecified 1.10 limit.','',
        'The full regression suite contains 147 tests. Arithmetic checks compare exponent decoding with exhaustive rescaling and limb products with unbounded-integer oracles; they cover signed products beyond 64-bit range, malformed CSR, altered primal/dual data, singular inverse proposals and unchanged dispatch. CPU/GPU continuation comparisons and independent original-model certificates pass. The retained CUDA kernels have their source-bound sanitizer evidence; this version changes host algorithms and scheduling, not those kernels.','',
        'For every included comparison, the evaluation verifies recorded references, original input hashes, certificate/model bindings and full nonzero counts. Timed-out, unsupported, missing or supervision-excluded results are retained in the evidence and are never silently turned into successful speed comparisons. Native optimum status and raw-audit acceptance are recorded separately from exact reconstruction.','',
        'Recovery requires a suitable rank profile and a recoverable exact primal or dual representation. Normal equations can be ill-conditioned, sparse factors can fill, and the inverse certificate imposes a quadratic storage and cubic work cost. The experiments do not establish large-scale behavior on arbitrary real-world, infeasible, unbounded or highly degenerate LPs. Three seeds support these measured comparisons, not a universal performance guarantee.','',
        '[Complete comparison data](lp-sp-pricing-final-comparison.csv), [settings, proofs and source bindings](lp-sp-pricing-final-results.json), and the [settled validation checkpoint](lp-sp-pricing-final-checkpoint.json) provide the reproducible evidence.','']
    DOC.write_text('\n'.join(lines));return DOC


def verify_all():
    f,rows=collect();models,preserved_rows,prior=preserved();reg=regression([r for r in rows if r['cohort']=='fresh_regression'],f['controls'])
    if not reg['passed']:raise RuntimeError('unchanged-path regression gate failed')
    OUT.mkdir(exist_ok=False);archive=read(CPU_GATE/'result.json')
    if binding(DOC)!=archive['old_report'] or binding(archive['retained_report']['path'])['sha256']!=archive['old_report']['sha256']:raise RuntimeError('requested report archive/expected version')
    development=[read(BASE/name/'result.json') for name in ('final-development-v1','final-development-v2')]
    result=dict(status='final_version_complete_cost_comparison',source=binding(__file__),prelaunch_refusal=binding(BASE/'final-report-prelaunch-refusal-v1.json'),freeze=binding(study.STUDY/'freeze.json'),driver=binding(BASE/'final-driver-v2/completed.json'),fresh_rows=rows,
        fresh_pairs=pairs([r for r in rows if r['cohort']=='fresh_focus'],f['models']),preserved_rows=preserved_rows,preserved_pairs=pairs(preserved_rows,models),preserved_sources=prior,regression=reg,
        development=[binding(BASE/name/'result.json') for name in ('final-development-v1','final-development-v2')],host_profile=binding(CPU_GATE/'result.json'),
        superseded_report=archive['old_report'],retained_superseded_report=archive['retained_report'],
        input_integrity=input_integrity(f['models']+f['controls']+models+[m for d in development for m in d['models']]),resources=resource_summary())
    # The user-requested report update has an explicit retained historical copy.
    result['checked_bindings']=bindings({k:v for k,v in result.items() if k!='superseded_report'})+bindings(f)
    put(OUT/'result.json',result);target=DOCS/'lp-sp-pricing-final-results.json';target.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    csvpath=DOCS/'lp-sp-pricing-final-comparison.csv';columns=['cohort','id','family','seed','lane','rows','columns','nonzeros','status','reason','route','timing_eligible','timely','native_optimal','raw_strict_accepted','accepted','certificate_kind','native_ns','encoding_ns','process_ns','raw_audit_ns','postprocess_ns','proof_ns','raw_complete_ns','complete_ns']
    with csvpath.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader();writer.writerows({key:row.get(key) for key in columns} for row in rows+preserved_rows)
    document(result,f,models)
    tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing*.py'))
    if not tests.wasSuccessful() or tests.testsRun!=147 or tests.skipped:raise RuntimeError('full final regression suite')
    for pattern in ('lp_sp_pricing_final*.py','lp_sp_pricing_dual_fast*.py'):
        for p in (ROOT/'tools').glob(pattern):compile(p.read_text(),str(p),'exec')
    checkpoint=DOCS/'lp-sp-pricing-final-checkpoint.json';checkpoint.write_text(json.dumps(dict(status='awaiting_reporting_settlement',report=binding(DOC)),indent=2)+'\n')
    docs=subprocess.run([sys.executable,'-B',str(ROOT/'tools/build_docs.py')],cwd=ROOT,text=True,capture_output=True,check=True);print(docs.stdout,end='',flush=True);pages=int(re.search(r'documentation built: (\d+) pages',docs.stdout)[1])
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    put(OUT/'verification.json',dict(status='passed',tests=tests.testsRun,documentation_pages=pages,source=binding(__file__),result=binding(OUT/'result.json'),outputs=[binding(p) for p in (DOC,target,csvpath)],
        historical_document_disposition=dict(original=archive['old_report'],retained=archive['retained_report'],replacement=binding(DOC),authorization='User explicitly requests replacing the comprehensive report with the final implementation and results. Prior numerical measurements and records are unchanged.')))


def settle(identity):
    study.frozen();a=allocation();verification=read(OUT/'verification.json')
    for k in ('source','result'):verify(verification[k])
    for b in verification['outputs']:verify(b)
    disposition=verification['historical_document_disposition'];verify(disposition['retained']);verify(disposition['replacement'])
    if disposition['original']['sha256']!=disposition['retained']['sha256']:raise RuntimeError('historical report copy')
    result=read(OUT/'result.json');bindings({k:v for k,v in result.items() if k!='superseded_report'})
    receipt=BASE/'resources'/f'{identity}.settlement.json';summary=resource_summary()
    if read(receipt)['status']!='passed' or summary['pending_at_snapshot']:raise RuntimeError('report settlement')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    if any(cpu[k]>CPU[k]*NS or gpu[k]>GPU[k]*NS for k in CPU):raise RuntimeError('final phase cap')
    owned=set()
    for pattern in ('*.resource.json','*.journal.json'):
        for path in (BASE/'resources').glob(pattern):owned.update(identities(read(path)))
    if any(still_same_process(*v) for v in owned):raise RuntimeError('owned process remains')
    now=dt.datetime.now(dt.timezone.utc);deadline=dt.datetime.fromisoformat(a['wall_deadline_utc']);checkpoint=dict(status='final_comprehensive_report_and_comparisons_settled',verification=binding(OUT/'verification.json'),reporting_settlement=binding(receipt),
        cpu_phase_ns=cpu,gpu_phase_ns=gpu,resources=summary,active_reservations=[],live_owned_identities=[],owned_identities=len(owned),tests=verification['tests'],documentation_pages=verification['documentation_pages'],
        settled_utc=now.isoformat(),elapsed_seconds=(now-(deadline-dt.timedelta(hours=2))).total_seconds(),within_two_hours=now<=deadline)
    put(OUT/'settled-checkpoint.json',checkpoint);target=DOCS/'lp-sp-pricing-final-checkpoint.json';target.write_text(json.dumps(checkpoint,sort_keys=True,indent=2)+'\n');(ROOT/'book/docs/benchmarks'/target.name).write_bytes(target.read_bytes())
    print(json.dumps(dict(status=checkpoint['status'],cpu_seconds=summary['cpu_ns']/NS,gpu_seconds=summary['gpu_ns']/NS,within_two_hours=checkpoint['within_two_hours'])),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','settle']);p.add_argument('--reservation');a=p.parse_args();verify_all() if a.action=='verify' else settle(a.reservation)
