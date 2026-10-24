"""Predeclared conservative forecast. Frozen before any device observations."""
from lp_protocol import read_json,write_json,file_hash
import math

RULE=dict(identity='gpup-tensor-cost-forecast-v1',threshold=0.9,
 retained_tuned_seconds={'gpup-development-dense_block-1024':0.462114,'gpup-extension-dense_block-65536':6.331022},
 required_profiles=16,horizon=2000,
 formula='cumulative execute envelope through first fresh certificate + final fresh host assessment + maximum measured producer tail across all profiles',
 prefix_includes='preparation, norm, context, upload, solve and boundary assessments; counted once',
 nonoverlap=True,negative_residual='refuse',source_changes_after_observation='refuse')

def integer(value):
 if type(value) is not int or value<0:raise ValueError('invalid physical counter')
 return value

def profile_complete(e,j,trial,worker):
 if trial['status']!='completed' or worker['reason']!='completed' or worker['returncode']!=0:return False
 if j['configuration']['backend']=='cuda-lp-tuned':
  return e['record']['backend']=='cuda-lp-tuned' and e['record']['termination']=='optimal' and e['assessment']['gap_closed']
 o=e['outcome'];return e['executor']=='gpu' and o['core']['iterations']==2000 and o['core']['stop']=='work_horizon' and o['core']['failure'] is None and o['counts']['uncertain']==0

def forecast(v,d,identity,persist=True):
 from benchmark_lp_tensor_warp32 import jobs,verify_endpoint
 from benchmark_lp_adaptive_cost import endpoint_shape
 if read_json(d/'forecast-rule.json')!=RULE:raise ValueError('forecast rule differs from frozen source')
 rows=[];tails=[];eligible=True
 for j in jobs(v):
  if j['kind']!='profile':continue
  key=j['id']
  if not all((d/(key+suffix)).exists() for suffix in ['.trial.json','.worker.json','.endpoint.json']):
   eligible=False;rows.append(dict(id=key,model=j['instance']['id'],configuration=j['configuration']['id'],ablation=j.get('ablation'),complete=False,useful=False,missing=True));continue
  trial=read_json(d/(key+'.trial.json'));worker=read_json(d/(key+'.worker.json'))
  verify_endpoint(v,j,d,identity)
  raw=read_json(d/(key+'.endpoint.json'));custom=j['configuration']['backend']!='cuda-lp-tuned'
  e=raw if custom else endpoint_shape(d/(key+'.endpoint.json'),'compact-v1')
  complete=profile_complete(e,j,trial,worker);eligible=eligible and complete
  if custom:envelope=integer(e['phases_ns']['execute_total'])
  else:envelope=integer(read_json(d/(key+'.raw-cost.json'))['elapsed_ns'])
  elapsed=integer(worker['elapsed_ns'])
  if envelope>elapsed:raise ValueError('negative producer tail')
  tails.append(elapsed-envelope)
  row=dict(id=key,model=j['instance']['id'],configuration=j['configuration']['id'],ablation=j.get('ablation'),complete=bool(complete),producer_tail_ns=elapsed-envelope)
  if custom:
   o=e['outcome'];c=o['counts'];first=o.get('first_certified_iteration')
   if first is None:first=o['core'].get('first_certified_iteration')
   row.update(first_certified_iteration=first,useful=c['useful_windows']>0 and c['mma_instructions']>0 and c['accepted_nonzero_t']>0 and c['accepted_nonzero_f']>0)
   if type(first) is int and 0<first<=2000:
    prefix=integer(e['phases_ns']['boundary/'+str(first)+'/execute_total']);final=integer(e['phases_ns']['delivery_original_assessment'])
    if prefix>envelope or final>envelope:raise ValueError('invalid phase envelope')
    row.update(prefix_ns=prefix,final_assessment_ns=final)
  rows.append(row)
 tail=max(tails,default=0);forecasts=[]
 for row in rows:
  if row['ablation'] is not None or row['configuration'] not in ['int8-tensor','fp16-tensor','bf16-tensor']:continue
  ns=row['prefix_ns']+row['final_assessment_ns']+tail if 'prefix_ns' in row else None
  forecasts.append(dict(model=row['model'],configuration=row['configuration'],forecast_ns=ns,passes=bool(ns is not None and row['useful'] and ns<=RULE['threshold']*RULE['retained_tuned_seconds'][row['model']]*1e9)))
 families=all(any(r['model']==model and r['configuration']=='int8-tensor' and r.get('useful') for r in rows if r['ablation'] is None) and any(r['model']==model and r['configuration'] in ['fp16-tensor','bf16-tensor'] and r.get('useful') for r in rows if r['ablation'] is None) for model in v['timing_instances'])
 result=dict(identity=RULE['identity'],passed=bool(len(rows)==16 and eligible and families and any(r['passes'] for r in forecasts)),profiles_complete=eligible,working_families=families,maximum_producer_tail_ns=tail,rows=rows,forecasts=forecasts,rule_sha256=file_hash(d/'forecast-rule.json'))
 if persist:
  path=d/'forecast.json'
  if path.exists() and read_json(path)!=result:raise ValueError('forecast already exists with different result')
  if not path.exists():write_json(path,result)
 return result


RESOURCE_RULE=dict(identity='gpup-tensor-warp32-resource-fit-v1',multiplier=1.25,
 repetitions=5,screening_seconds=300,missing_input='refuse',
 formula='five repetitions of every model/configuration first-certificate envelope plus maximum lease tail; 1.25 factor; maximum complete-profile coordinator time outside leases charged for all 60 cells; four-times-wall CPU')


def resource_estimate(v,d,identity):
 from benchmark_lp_tensor_warp32 import jobs,verify_endpoint
 from benchmark_lp_adaptive_cost import endpoint_shape
 if read_json(d/'resource-rule.json')!=RESOURCE_RULE:raise ValueError('resource estimator differs from freeze')
 samples=[];lease_tails=[];outside=[]
 for j in jobs(v):
  if j['kind']!='profile':continue
  key=j['id'];trial=read_json(d/(key+'.trial.json'));worker=read_json(d/(key+'.worker.json'))
  verify_endpoint(v,j,d,identity)
  custom=j['configuration']['backend']!='cuda-lp-tuned';e=read_json(d/(key+'.endpoint.json')) if custom else endpoint_shape(d/(key+'.endpoint.json'),'compact-v1')
  if not profile_complete(e,j,trial,worker):return dict(available=False,reason='incomplete_profile')
  leased=integer(worker['leased_ns']);elapsed=integer(worker['elapsed_ns']);coordinator=integer(trial['coordinator_wall_ns'])
  if leased<elapsed or coordinator<leased:raise ValueError('negative lease/coordinator tail')
  lease_tails.append(leased-elapsed);outside.append(coordinator-leased)
  if 'ablation' in j:continue
  if custom:
   first=e['outcome'].get('first_certified_iteration',e['outcome']['core'].get('first_certified_iteration'))
   if type(first) is not int or not 0<first<=2000:return dict(available=False,reason='missing_first_certificate')
   envelope=integer(e['phases_ns']['execute_total']);prefix=integer(e['phases_ns']['boundary/'+str(first)+'/execute_total']);final=integer(e['phases_ns']['delivery_original_assessment'])
   if max(prefix,final)>envelope or envelope>elapsed:raise ValueError('invalid resource forecast envelope')
   producer=prefix+final
   samples.append(dict(model=j['instance']['id'],configuration=j['configuration']['id'],producer_ns=producer,tail_ns=elapsed-envelope))
  else:samples.append(dict(model=j['instance']['id'],configuration=j['configuration']['id'],producer_ns=elapsed,tail_ns=0))
 if len(samples)!=12:return dict(available=False,reason='missing_configuration')
 maximum_producer_tail=max(r['tail_ns'] for r in samples);lease_tail=max(lease_tails);maximum_outside=max(outside)
 # Apply the largest observed producer tail to every research configuration.
 total=sum(r['producer_ns']+(0 if r['configuration']=='tuned-fp64' else maximum_producer_tail)+lease_tail for r in samples)*5
 leased_estimate=math.ceil(1.25*total);outside_estimate=math.ceil(1.25*60*maximum_outside)
 return dict(available=True,leased_ns=leased_estimate,outside_ns=outside_estimate,
             cpu_ns=4*(leased_estimate+outside_estimate+2_000_000_000),
             maximum_lease_tail_ns=lease_tail,maximum_outside_lease_ns=maximum_outside,samples=samples)


def resource_forecast(v,d,identity):
 from lp_tensor_warp32_common import worker_remaining_ns
 estimate=resource_estimate(v,d,identity)
 available_cpu_ns=4*worker_remaining_ns()
 result=dict(identity=RESOURCE_RULE['identity'],estimate=estimate,available_worker_cpu_ns=available_cpu_ns,
             passed=bool(estimate['available'] and estimate['leased_ns']<=300_000_000_000 and estimate['cpu_ns']<=available_cpu_ns),
             rule_sha256=file_hash(d/'resource-rule.json'))
 path=d/'resource-fit.json'
 if path.exists():
  previous=read_json(path)
  if previous['estimate']!=estimate or previous['rule_sha256']!=result['rule_sha256']:raise ValueError('resource forecast changed')
  return previous
 write_json(path,result)
 return result
