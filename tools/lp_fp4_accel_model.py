"""Original-model fixtures for SPEC-0031; generated solutions are checker tests only."""
import math
import numpy as np
from lp_fp4_integrate_model import FAMILIES as PRIOR_FAMILIES, model as prior_model
from lp_fp4_fast_prepare import encode_batch,FP4_VALUES

FAMILIES = (*PRIOR_FAMILIES, 'dense-generic-128', 'dense-generic-256',
            'dense-generic-512', 'ill-scaled-generic-128')
LANES = ('native', 'fp4x2', 'fp4x4', 'auto')


def model(family):
    if family in PRIOR_FAMILIES:
        return prior_model(family)
    if family not in FAMILIES:
        raise ValueError('unknown fixture')
    n = int(family.rsplit('-', 1)[1])
    i = np.arange(n)
    a = np.eye(n) + (((13*i[:, None] + 7*i[None, :]) % 37) - 18)/(73*n)
    if family.startswith('ill-scaled'):
        a *= np.exp2(i % 9 - 4)[:, None]
    x = (13*i % 37)/37 - .5
    y = (7*i % 29)/29 - .5
    c = a.T @ y
    rhs = a @ x
    sense = 'maximize' if n == 256 else 'minimize'
    def bound(v):
        return dict(kind='finite', value=float(v))
    doc = dict(schema_version=1, model_id='fp4-accel-v1-'+family,
        variables=[dict(id=3*j+7, domain='continuous', lower=bound(-1), upper=bound(1)) for j in range(n)],
        constraints=[dict(id=5*r+11, lower=bound(rhs[r]), upper=bound(rhs[r]),
            terms=[dict(variable_id=3*j+7, coefficient=float(a[r,j])) for j in range(n) if a[r,j]!=0]) for r in range(n)],
        objective=dict(sense=sense, offset=3.25,
            terms=[dict(variable_id=3*j+7, coefficient=float(c[j] if sense=='minimize' else -c[j])) for j in range(n) if c[j]!=0]))
    return doc, dict(a=a, c=c, lo=np.full(n,-1.), hi=np.full(n,1.), rl=rhs, ru=rhs,
                     target_x=x, target_y=y)


def reference(data, raw, steps, shift, row_scale):
    """Independent original-coefficient CPU recurrence in explicit scaled coordinates."""
    a=data['a']*np.asarray(row_scale)[:,None]
    n=len(data['c']);p=((n+31)//32)*32
    result=np.asarray(raw).reshape(5,p).copy();tau=math.ldexp(1.,-shift)
    for _ in range(steps):
        old=result[0,:n].copy()
        x=np.clip(old+tau*(a.T@result[1,:n]-data['c']),data['lo'],data['hi'])
        result[0,:n]=x;result[2,:n]=2*x-old
        y=result[1,:n]-tau*(a@result[2,:n])
        result[1,:n]=y-np.clip(y,-tau*data['ru']*row_scale,-tau*data['rl']*row_scale)
    return result.reshape(-1)


def represented(values,k):
    values=np.asarray(values);words,scales=encode_batch(values,4,k,arrays=True)
    codes=((words.reshape(len(values),k,-1)[...,None]>>np.arange(0,32,4))&15).reshape(len(values),k,-1)
    decoded=FP4_VALUES[codes&7]*np.where(codes&8,-1.,1.)
    return np.ldexp(decoded,scales.reshape(len(values),k,1)).sum(axis=1)


def reference_centered(data,raw,steps,shift,row_scale,k):
    """Independent FP64 component oracle for one window with frozen original products."""
    n=len(data['c']);p=((n+31)//32)*32;b=p//32;tau=math.ldexp(1.,-shift)
    a=np.zeros((p,p));a[:n,:n]=data['a']*np.asarray(row_scale)[:,None]
    tiles=a.reshape(b,32,b,32).transpose(0,2,1,3).reshape(b*b,1024)
    a0=represented(tiles,k).reshape(b,b,32,32).transpose(0,2,1,3).reshape(p,p)
    out=np.asarray(raw).reshape(5,p).copy();base_x=out[0].copy();base_y=out[1].copy()
    ax=a@base_x;aty=a.T@base_y
    for _ in range(steps):
        qy=represented((out[1]-base_y).reshape(b,32),k).reshape(p)
        at=aty+a0.T@qy;old=out[0].copy()
        x=np.clip(old[:n]+tau*(at[:n]-data['c']),data['lo'],data['hi'])
        out[0,:n]=x;out[2]=2*out[0]-old
        qb=represented((out[2]-base_x).reshape(b,32),k).reshape(p)
        ab=ax+a0@qb;y=out[1,:n]-tau*ab[:n]
        out[1,:n]=y-np.clip(y,-tau*data['ru']*row_scale,-tau*data['rl']*row_scale)
    return out.reshape(-1)
