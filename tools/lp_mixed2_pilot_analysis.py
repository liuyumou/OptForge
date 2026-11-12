"""Portable replay and descriptive analysis; no adoption decision from pilot data."""
import argparse
from fractions import Fraction as F
import gzip
import json
import math
from pathlib import Path
import statistics as stats
import struct
from lp_mixed2_pilot_common import ROOT,BASE,TARGETS,load,put,ref,require
from lp_mixed2_pilot_validate import profile,exact_solve,original_dots,check_guard
from lp_delivery2_study import bits
DATA=ROOT/'docs/benchmarks/data'
ARCHIVE=DATA/'mixed2-pilot-records-v1.json.gz'
OUTPUT=DATA/'mixed2-pilot-analysis-v1.json'


def describe(values):
    return dict(median=stats.median(values),minimum=min(values),maximum=max(values),blocks=values)


def oracle(inp,fp32):
    n,m=inp['rows'],inp['cols'];p=((max(n,m)+31)//32)*32;tr=inp['transpose']
    a=[float(struct.unpack('f',struct.pack('f',v))[0]) if fp32 else v for v in inp['a']]
    a=list(map(F,a));x=list(map(F,inp['x']));out=[]
    for i in range(m if tr else n):
        partial=[]
        for w in range(8):
            acc=0.
            for j in range(w,p,8):
                term=(a[j*m+i] if tr else a[i*m+j])*x[j] if j<(n if tr else m) else F(0)
                acc=float(term+F(acc))
            partial.append(acc)
        total=0.
        for value in partial:total+=value
        out.append(total)
    return out+[0.]*(p-len(out))


def package():
    m=load(BASE/'study-v1/manifest.json');sessions=[];products=[];originals={}
    for block in range(8):
        r=load(BASE/f'study-v1/block-{block}/result.json');require(r['status']=='complete','incomplete block')
        for row in r['sessions']:
            originals[row['family']]=load(ROOT/row['original']['path'])
            sessions.append(dict(**row,values=[load(ROOT/v['result']['path']) for v in row['records']],log_values=[json.loads(x) for x in (ROOT/row['profile_log']['path']).read_text().splitlines()]))
        for row in r['products']:products.append(dict(**row,input_value=load(ROOT/row['input']['path'])))
    record=dict(manifest=m,manifest_binding=ref(BASE/'study-v1/manifest.json'),sessions=sessions,products=products,originals=originals)
    with ARCHIVE.open('xb') as f:f.write(gzip.compress(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False).encode(),mtime=0))
    put(OUTPUT,analyze(record));print(dict(packaged_sessions=len(sessions),products=len(products)),flush=True)


def analyze(record):
    m=record['manifest'];sessions=record['sessions'];products=record['products'];index={};pindex={};certificates=0
    require(len(sessions)==192 and len(products)==192,'pilot coverage')
    require(set(m['models'])==set(record['originals']) and len(m['models'])==12,'family coverage')
    require({r['id'] for r in sessions}=={r['id'] for r in m['sessions']},'session manifest mismatch')
    require({r['id'] for r in products}=={r['id'] for r in m['products']},'product manifest mismatch')
    for row in sessions:
        key=(row['block'],row['family'],row['variant']);require(key not in index,'duplicate session');index[key]=row
        require(len(row['values'])==len(row['records'])==3,'solve coverage')
        for receipt,value in zip(row['records'],row['values']):
            exact_solve(value,record['originals'][row['family']],m['binary'],m['image'])
            require(value['certified']==(row['family']!='infinite-bound-refusal'),'coverage authority')
            require(receipt['complete_ns']>=value['solve_ns'],'incomplete delivery');certificates+=value['certified']
        require(profile(row['log_values'])==row['profile'],'profile replay')
        if row['variant']=='control':require(row['profile']['windows']==0,'control profiled')
    exact_cache={};oracle_cache={};guard_outputs=0
    for row in products:
        key=(row['block'],row['family'],row['transpose'],row['mode']);require(key not in pindex,'duplicate product');pindex[key]=row
        inp=row['input_value'];v=row['value'];require(v['count']==128 and v['gpu_ns']>0 and row['complete_ns']>v['launch_sync_ns'],'product boundary')
        cache_key=(row['family'],row['transpose'],row['mode']=='fp64')
        if cache_key not in oracle_cache:oracle_cache[cache_key]=oracle(inp,row['mode']!='fp64')
        expected=oracle_cache[cache_key];require(bits(v['expected'])==bits(expected),'independent FMA schedule oracle')
        if row['mode']!='guard':require(bits(v['values'])==bits(expected),'device product mismatch')
        require(all(a<=b for a,b in zip(v['timer'],v['timer'][1:])),'timer nonmonotonic')
    prepared=[];product_rows=[]
    for family in m['models']:
        controls=[index[b,family,'control'] for b in range(8)];profiles=[index[b,family,'profile'] for b in range(8)]
        def mean_time(row):return stats.mean(v['complete_ns'] for v in row['records'])
        t=[mean_time(r) for r in controls];pt=[mean_time(r) for r in profiles]
        g=[stats.mean(v['gpu_us']*1000 for v in r['values']) for r in controls]
        matrix=[r['profile']['matrix_union_ns']/3 for r in profiles]
        prepared.append(dict(family=family,control_ms=describe([v/1e6 for v in t]),profile_ms=describe([v/1e6 for v in pt]),profile_over_control=describe([b/a for a,b in zip(t,pt)]),control_gpu_ms=describe([v/1e6 for v in g]),profile_matrix_ms=describe([v/1e6 for v in matrix]),profile_cta_ms=describe([r['profile']['cta_union_ns']/3e6 for r in profiles]),profile_kernel_event_ms=describe([r['profile']['kernel_event_ns']/3e6 for r in profiles]),profile_outer_event_ms=describe([r['profile']['outer_event_ns']/3e6 for r in profiles]),control_setup_ms=describe([r['setup_ns']/1e6 for r in controls]),control_teardown_ms=describe([r['teardown_ns']/1e6 for r in controls]),lifecycle_forecasts=[dict(solves=n,all_event_2x_ratio=describe([(r['setup_ns']+r['teardown_ns']+n*t[b])/(r['setup_ns']+r['teardown_ns']+n*(t[b]-g[b]/2)) for b,r in enumerate(controls)])) for n in (1,3,100)],whole_event_2x_forecast=describe([a/(a-b/2) for a,b in zip(t,g)]),whole_event_removal_forecast=describe([a/(a-b) for a,b in zip(t,g)])))
    for family in (*TARGETS,'irregular-tail-33'):
        for tr in (False,True):
            groups=[{mode:pindex[b,family,tr,mode] for mode in ('fp64','fp32','guard')} for b in range(8)]
            for group in groups:
                inp=group['fp32']['input_value'];key=(family,tr)
                if key not in exact_cache:exact_cache[key]=original_dots(inp)
                check=check_guard(inp,group['fp32']['value']['values'],group['guard']['value']['values'],exact_cache[key]);guard_outputs+=check['outputs']
            ns={mode:[r[mode]['value']['gpu_ns']/128 for r in groups] for mode in ('fp64','fp32','guard')}
            v=[r['fp32']['value'] for r in groups]
            product_rows.append(dict(family=family,transpose=tr,fp64_us=describe([x/1000 for x in ns['fp64']]),fp32_us=describe([x/1000 for x in ns['fp32']]),guard_us=describe([x/1000 for x in ns['guard']]),product_speed_ratio=describe([a/b for a,b in zip(ns['fp64'],ns['fp32'])]),guarded_speed_ratio=describe([a/(b+c) for a,b,c in zip(ns['fp64'],ns['fp32'],ns['guard'])]),saved_ns=[a-b for a,b in zip(ns['fp64'],ns['fp32'])],guarded_saved_ns=[a-b-c for a,b,c in zip(ns['fp64'],ns['fp32'],ns['guard'])],representation_us=describe([r['representation_ns']/1000 for r in v]),fp32_upload_us=describe([r['h2d_fp32_ns']/1000 for r in v]),error_upload_us=describe([r['h2d_error_ns']/1000 for r in v]),download_us=describe([r['d2h_ns']/1000 for r in v]),matrix_bytes=v[0]['matrix_bytes'],amortization_scenarios=[dict(products=n,readback=readback,ratio=describe([n*(ns['fp64'][b]+(group['fp64']['value']['d2h_ns'] if readback else 0))/(v[b]['representation_ns']+v[b]['h2d_fp32_ns']+v[b]['h2d_error_ns']+n*(ns['fp32'][b]+ns['guard'][b]+(v[b]['d2h_ns']+group['guard']['value']['d2h_ns'] if readback else 0))) for b,group in enumerate(groups)])) for n in (1,128,4096) for readback in (False,True)],timer_min_positive_ns=min((b-a for r in v for a,b in zip(r['timer'],r['timer'][1:]) if b>a),default=None)))
    for family in m['models']:
        require(sum(index[b,family,'control']['position']==0 for b in range(8))==4,'unbalanced pair order')
    return dict(status='complete-diagnostic-only',archive=ref(ARCHIVE),sessions=len(sessions),solves=3*len(sessions),certificates=certificates,intentional_refusals=3*len(sessions)-certificates,product_cells=len(products),guarded_outputs=guard_outputs,prepared=prepared,products=product_rows,adoption_decision=None,uncertainty='Eight descriptive block values and range; no simultaneous adoption interval or power claim',limitations=['Target-specific instrumented timestamps; profiling changes execution','Stream-batch product events include host launch gaps','Representation builds all three matrix arrays; incremental CPU packing cost is not identified','Product operands are fixed; useful mixed windows, work amplification and recovery are unmeasured','Shared device and sequential fresh sessions do not establish independent production samples'])


def verify():
    record=json.loads(gzip.decompress(ARCHIVE.read_bytes()));require(analyze(record)==load(OUTPUT),'portable analysis mismatch');print('MIXED2 pilot portable replay passed',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['package','verify']);a=p.parse_args();globals()[a.action]()
