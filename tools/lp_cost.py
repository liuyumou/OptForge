"""Hierarchical component costs and strict reconciliation; diagnostics, never proofs."""
from contextlib import contextmanager
import time

class Profile:
    def __init__(self,enabled):
        self.enabled=enabled;self.origin=time.monotonic_ns() if enabled else None
        self.stack=[];self.rows={};self.counters={};self.unavailable=[]
    @contextmanager
    def scope(self,name):
        if not self.enabled:
            yield;return
        path=tuple(f[0] for f in self.stack)+(name,);frame=[name,time.monotonic_ns(),0]
        self.stack.append(frame)
        try:yield
        finally:
            inclusive=time.monotonic_ns()-frame[1];self.stack.pop()
            if self.stack:self.stack[-1][2]+=inclusive
            row=self.rows.setdefault(path,dict(path=list(path),calls=0,inclusive_ns=0,exclusive_ns=0,min_ns=inclusive,max_ns=inclusive))
            row['calls']+=1;row['inclusive_ns']+=inclusive;row['exclusive_ns']+=inclusive-frame[2]
            row['min_ns']=min(row['min_ns'],inclusive);row['max_ns']=max(row['max_ns'],inclusive)
    def finish(self):
        if not self.enabled:return None
        return dict(schema_version=1,clock='monotonic_host_thread',elapsed_ns=time.monotonic_ns()-self.origin,
                    scopes=sorted(self.rows.values(),key=lambda v:v['path']),counters=self.counters,
                    unavailable=self.unavailable+(['unclosed scopes: partial host attribution'] if self.stack else []))

def validate_profile(profile):
    from validate_artifacts import validator
    validator('lp-cost-raw-v1.schema.json').validate(profile)
    scopes={tuple(s['path']):s for s in profile['scopes']}
    if len(scopes)!=len(profile['scopes']):raise ValueError('duplicate component path')
    partial_stack=any(u in ['unclosed scopes: partial host attribution','scope closed out of stack order'] for u in profile['unavailable'])
    total=0
    for path,s in scopes.items():
        if s['exclusive_ns']>s['inclusive_ns'] or s['min_ns']>s['max_ns'] or not s['min_ns']*s['calls']<=s['inclusive_ns']<=s['max_ns']*s['calls']:
            raise ValueError('inconsistent component duration')
        children=sum(v['inclusive_ns'] for k,v in scopes.items() if len(k)==len(path)+1 and k[:-1]==path)
        if s['inclusive_ns']!=s['exclusive_ns']+children or (not partial_stack and len(path)>1 and path[:-1] not in scopes):
            raise ValueError('component hierarchy does not reconcile')
        total+=s['exclusive_ns']
    if total>profile['elapsed_ns']:raise ValueError('exclusive component costs exceed envelope')
    return profile['elapsed_ns']-total

def interval_union(intervals):
    """Busy wall duration; concurrent intervals are not added twice."""
    end=None;total=0
    for lo,hi in sorted(intervals):
        if lo<0 or hi<lo:raise ValueError('invalid activity interval')
        total+=max(0,hi-max(lo,end if end is not None else lo));end=max(hi,end or hi)
    return total
