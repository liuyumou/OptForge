"""Opt-in practical solver using sparse reductions and factorized geometry."""
from fractions import Fraction as Q
from .compact_basis import Rows, Storage, NullRows, PairedRows, sparse_rref, product
from .compact_geometry import CompactCalibration, CompactOracle
from .exact import Limit, rational, dot
from .lp import certificate
from .market import Market, median
from .solver import PricingSolver


class GeneratedRows:
    def __init__(self,r,s,row):self.r=r;self.s=s;self.row=row
    def __len__(self):return self.r
    def column(self,j):return {i:q for i in range(self.r) if (q:=self.row(i).get(j))}


def slack_factors(a,b,work,storage):
    columns=[{} for _ in range(a.s)]
    for i in range(a.r):
        for j,q in a.row(i).items():columns[j][i]=-q
        work.tick(count=len(a.row(i)))
    def generators():
        yield from columns
        yield {a.r:Q(1),**{i:q for i,q in enumerate(b) if q}}
    return sparse_rref(generators(),a.r+1,work,storage)


def solve_sparse(a,b,work,storage):
    rows=({**a.row(i),a.s:b[i]} if b[i] else dict(a.row(i)) for i in range(a.r))
    reduced,pivots=sparse_rref(rows,a.s+1,work,storage,coefficient_columns=a.s)
    if any(row.get(a.s) and not any(j<a.s for j in row) for row in reduced.rows):return None
    x=[Q(0)]*a.s
    for i,pivot in enumerate(pivots):x[pivot]=reduced.row(i).get(a.s,Q(0))
    return x


class CompactSolver(PricingSolver):
    def __init__(self,*args,storage=None,**kwargs):
        super().__init__(*args,**kwargs);self.storage=storage or Storage();self.compact_profiles=[]

    def recover_compact(self,c,pivots,target,signs):
        side=signs[target];selected=c if side==1 else NullRows(c,pivots)
        if not selected.r:return None
        # Cheap exact witnesses are useful before constructing any recovery LP.
        for i in range(selected.r):
            row=selected.row(i);q=row.get(target)
            if q and all(v/q>=0 and signs[j]==side for j,v in row.items()):
                return side,[row.get(j,Q(0))/q for j in range(selected.s)]
            self.work.tick(count=len(row))
        constraints=(selected.column(j) for j,sign in enumerate(signs) if sign!=side)
        restricted,p=sparse_rref(constraints,selected.r,self.work,self.storage)
        coefficients=NullRows(restricted,p)
        if not coefficients.r:return None
        def combined(i):
            answer={}
            for k,scale in coefficients.row(i).items():
                for j,q in selected.row(k).items():
                    value=answer.get(j,Q(0))+scale*q
                    if value:answer[j]=value
                    else:answer.pop(j,None)
                    self.work.tick(value,count=2)
            return answer
        space=GeneratedRows(coefficients.r,selected.s,combined)
        if (space.s+2)*(2*space.r+2)>1000000:raise Limit('compact_recovery_tableau_limit')
        a=[[Q(0)]*space.r for _ in range(space.s)]
        for i in range(space.r):
            for j,q in space.row(i).items():a[j][i]=-q
        rhs=[Q(-int(j==target)) for j in range(space.s)]
        self.recovery_lps+=1
        result=certificate(a,rhs,[Q(0)]*space.r,self.work)
        if result['status']=='infeasible':return None
        if result['status']!='optimal':raise ArithmeticError('bounded zero objective')
        vector=product(space,result['x'],True,self.work)
        if vector[target]<1 or any(v<0 for v in vector):raise ArithmeticError('invalid sparse recovery')
        return side,vector

    def feasibility(self,a,b,columns=None):
        if not isinstance(a,(Rows,GeneratedRows)):a=Rows.dense(a)
        with self.phase('geometry_and_experts'):
            c,pivots=slack_factors(a,b,self.work,self.storage)
            paired=PairedRows(c,pivots);calibration=CompactCalibration(paired,self.work,self.storage)
            n=a.r+1;market=Market(n,calibration.demand_bound,self.work,self.extra_experts,self.seed)
        profile=dict(ambient=n,original_nonzeros=sum(len(a.row(i)) for i in range(a.r)),
            stored_positive_entries=c.stored_entries,implicit_complement_rows=n-c.r,
            avoided_dense_paired_entries=2*n*n)
        self.compact_profiles.append(profile);prices_seen=[];epochs=1;extra=self.extra_experts
        for _ in range(self.max_queries-self.queries):
            self.work.tick()
            if len(prices_seen)>=min(market.round_bound(),4 if epochs==1 else 16):
                if epochs>=3 or extra>=65536:raise Limit('practical_expert_epoch_limit')
                extra=min(65536,max(4096,4*extra));epochs+=1
                market=Market(n,calibration.demand_bound,self.work,extra,self.seed)
                self.events.append(dict(kind='expert_expansion',epoch=epochs,extra_experts=extra,
                    preceding_queries=len(prices_seen),wealth_reset=True));prices_seen=[]
            with self.phase('market'):prices,market_proof=market.minimize(backend=self.market_backend)
            with self.phase('calibration'):
                calibrated=calibration.query(prices)
                oracle=CompactOracle(calibrated['basis'],calibrated['H'],calibrated['epsilon'],self.work,
                    calibrated['epoch'],calibrated['displacement_bound'])
            if not oracle.broadcast_negative:raise ArithmeticError('missing separation proof')
            with self.phase('auxiliary_labels'):labels,_=oracle.labels(self.batch_width,expected_epoch=0,gpu=self.gpu)
            self.queries+=1;prices_seen.append(prices)
            with self.phase('wealth_update'):market.update(prices,labels)
            self.events.append(dict(query=self.queries,auxiliary_calls=oracle.calls,
                fallback_constructions=oracle.fallback_constructions,gpu=oracle.gpu_metadata))
            with self.phase('exact_support_recovery'):
                recovered=self.recover_compact(c,pivots,n-1,labels)
                if not recovered and len(prices_seen)%2:
                    recovered=self.recover_compact(c,pivots,n-1,[1 if p>=0 else -1 for p in median(prices_seen)])
            if recovered:
                side,v=recovered
                if v[-1]<=0 or any(q<0 for q in v):raise ArithmeticError('invalid homogeneous witness')
                if side==1:
                    x=solve_sparse(a,[q-v[i]/v[-1] for i,q in enumerate(b)],self.work,self.storage)
                    if x is None or any(q>bound for q,bound in zip(product(a,x,False,self.work),b)):
                        raise ArithmeticError('sparse primal recovery failed')
                    return dict(status='feasible',x=x)
                y=v[:-1]
                if any(product(a,y,True,self.work)) or dot(b,y,self.work)>=0:raise ArithmeticError('sparse Farkas recovery failed')
                return dict(status='infeasible',y=y)
        raise Limit('practical_price_query_limit')

    def solve(self,model,mode='practical'):
        if mode!='practical':raise ValueError('compact path has no literal reference claim')
        a=model['A'] if isinstance(model['A'],(Rows,GeneratedRows)) else Rows.dense(model['A'])
        b,c=list(map(rational,model['b'])),list(map(rational,model['c']))
        n,m=a.s,a.r
        if len(b)!=m or len(c)!=n or model.get('sense','max')!='max':raise ValueError('canonical max Ax<=b')
        start=self.feasibility(a,b)
        if start['status']=='infeasible':return self.result(start)
        recession=GeneratedRows(m+1,n,lambda i:a.row(i) if i<m else {j:-q for j,q in enumerate(c) if q})
        ray=self.feasibility(recession,[Q(0)]*m+[Q(-1)])
        if ray['status']=='feasible':return self.result(dict(status='unbounded',x=start['x'],ray=ray['x']))
        columns=[{} for _ in range(n)]
        for i in range(m):
            for j,q in a.row(i).items():columns[j][n+i]=q
        gap={j:-q for j,q in enumerate(c) if q};gap.update({n+i:q for i,q in enumerate(b) if q})
        def optimality_row(i):
            if i<3*m:
                row_index,kind=divmod(i,3)
                if kind==1:return {n+row_index:Q(-1)}
                row=dict(a.row(row_index))
                if b[row_index]:row[n+m]=-b[row_index]
                if kind==2:row[n+row_index]=Q(-1)
                return row
            i-=3*m
            if i<2*n:
                j,negative=divmod(i,2);sign=-1 if negative else 1
                row={k:sign*q for k,q in columns[j].items()}
                if c[j]:row[n+m]=-sign*c[j]
                return row
            if i==2*n:return dict(gap)
            if i==2*n+1:return {j:-q for j,q in gap.items()}
            return {n+m:Q(-1)}
        mixed=GeneratedRows(3*m+2*n+3,n+m+1,optimality_row)
        limits=[Q(-int(i<3*m and i%3==2 or i==mixed.r-1)) for i in range(mixed.r)]
        optimum=self.feasibility(mixed,limits)
        if optimum['status']!='feasible':raise ArithmeticError('optimality alternatives disagree')
        alpha=optimum['x'][-1]
        if alpha<1:raise ArithmeticError('homogenizing coordinate')
        point=[q/alpha for q in optimum['x'][:-1]]
        return self.result(dict(status='optimal',x=point[:n],y=point[n:],value=dot(c,point[:n],self.work)))

    def result(self,proof):
        result=super().result(proof);result.update(compact_geometry=self.compact_profiles,
            storage_peak_entries=self.storage.peak_entries,storage_peak_estimated_bytes=self.storage.peak_bytes,
            calibration='compact_direct_input_height',search='restricted_flat_experts_compact_storage')
        return result
