"""Lazy exact oracle and sparse calibration of implicit paired rows."""
from contextlib import ExitStack
from fractions import Fraction as Q
import heapq

from .compact_basis import Rows, Storage, product
from .calibration import floor_log2, scaled_interval, scaled_square_greater
from .exact import Limit, rational
from .geometry import LabelOracle
from .native_auxiliary import NativeAuxiliary
from .lp import check


class CompactCalibration:
    def __init__(self, original, work, storage=None):
        if original.s%2 or not original.r:raise ValueError('paired basis')
        self.original=original;self.work=work;self.storage=storage or Storage()
        self.n=original.s//2;self.rank=original.r;self.epoch=0
        denominator_bits=self.rank*original.s;numerator_bits=0
        for i in range(original.r):
            row=original.row(i)
            denominator_bits+=sum(q.denominator.bit_length()-1 for q in row.values())
            numerator_bits=max(numerator_bits,max((abs(q.numerator).bit_length() for q in row.values()),default=0))
            work.tick(count=len(row))
        self.log_height=self.rank*(denominator_bits+numerator_bits+self.rank.bit_length()+2)+2
        self.demand_bound=2*self.log_height+3

    def query(self, prices, initial_bits=64):
        prices=list(map(rational,prices))
        if len(prices)!=self.n or any(p.denominator not in (1,2) for p in prices):raise ValueError('prices')
        bits=initial_bits
        while bits<=min(4096,self.work.max_bits//4):
            answer=self._query(prices,bits)
            if answer is not None:return answer
            bits*=2
        raise Limit('calibration_precision_limit')

    def _query(self,prices,bits):
        exponents=[p if slot==0 else -p for p in prices for slot in (0,1)]
        eliminated=[];pivot_index={};pivots=[];bounds=[];rows=[];column_bound={};error=Q(0)
        self.storage.reset()
        for i in range(self.rank):
            cofactor=dict(self.original.row(i));queue=[pivot_index[j] for j in cofactor if j in pivot_index]
            heapq.heapify(queue);queued=set(queue)
            while queue:
                k=heapq.heappop(queue);pivot=pivots[k];factor=cofactor.get(pivot)
                if not factor:continue
                previous=eliminated[k];factor/=previous[pivot]
                for j,q in previous.items():
                    value=cofactor.get(j,Q(0))-factor*q
                    if value:cofactor[j]=value
                    else:cofactor.pop(j,None)
                    index=pivot_index.get(j)
                    if value and index is not None and index>k and index not in queued:
                        heapq.heappush(queue,index);queued.add(index)
                    self.work.tick(value,count=2)
            if not cofactor:raise ValueError('dependent paired factors')
            available=sorted(cofactor);pivot=available[0]
            for j in available[1:]:
                if scaled_square_greater(cofactor[j]/cofactor[pivot],2*(exponents[j]-exponents[pivot]),self.work):pivot=j
            bound=1+column_bound.get(pivot,Q(0));bounds.append(bound);self.work.tick(bound)
            row={}
            for j,q in cofactor.items():
                lo,hi=scaled_interval(q/abs(cofactor[pivot]),exponents[j]-exponents[pivot],bits,self.work)
                midpoint=(lo+hi)/2
                if midpoint:row[j]=midpoint
                error=max(error,(hi-lo)/2)
                column_bound[j]=column_bound.get(j,Q(0))+max(abs(lo),abs(hi))*bound
            rows.append(row);eliminated.append(cofactor);pivot_index[pivot]=i;pivots.append(pivot)
            self.storage.observe(row);self.storage.observe(cofactor)
        h=max(bounds);eps=Q(1,1024*self.n);delta=self.rank*h*error
        if delta>eps/4:return None
        return dict(basis=Rows(rows,2*self.n),H=h,epsilon=eps,entry_error=error,
            coefficient_bounds=bounds,displacement_bound=delta,pivots=pivots,epoch=0,
            demand_bound=self.demand_bound,arithmetic_bits=bits,mode='compact_direct_calibration')


class CompactOracle(LabelOracle):
    def __init__(self,matrix,h,epsilon,work,epoch=0,isotropic_error=None):
        if matrix.s%2 or matrix.r<1:raise ValueError('paired matrix')
        self.matrix=matrix;self.r=matrix.r;self.n=matrix.s//2
        self.h,self.epsilon=rational(h),rational(epsilon);self.work=work;self.epoch=epoch
        if self.h<=0 or not 0<self.epsilon<Q(1,4):raise ValueError('auxiliary bounds')
        # Opposite-slot broadcast is disabled unless calibration supplied the
        # same exact displacement proof as the existing oracle.
        delta=None if isotropic_error is None else rational(isotropic_error)
        if delta is not None and delta<0:raise ValueError('negative displacement')
        lower=((Q(1,4)-self.epsilon)/2)**2-2*(self.n-1)*self.epsilon
        self.broadcast_negative=delta is not None and self.n*delta*(4+delta)<lower
        self._a=None;self._rhs=None;self.fallback_constructions=0;self.calls=0;self.gpu_metadata=None

    def fallback(self):
        if self._a is not None:return self._a,self._rhs
        constraints=2*self.r+4*self.n
        if (constraints+1)*(2*self.r+1)>1000000:raise Limit('compact_exact_fallback_tableau_limit')
        a=[];rhs=[]
        for i in range(self.r):
            row=[Q(int(i==j)) for j in range(self.r)];a.extend([row,[-v for v in row]]);rhs.extend([self.h,self.h])
        columns=[[] for _ in range(2*self.n)]
        for i in range(self.r):
            for j,q in self.matrix.row(i).items():columns[j].append((i,q))
        for column in columns:
            row=[Q(0)]*self.r
            for i,q in column:row[i]=q
            a.extend([row,[-v for v in row]]);rhs.extend([Q(2),self.epsilon])
        self._a,self._rhs=a,rhs;self.fallback_constructions+=1
        return a,rhs

    @property
    def a(self):return self.fallback()[0]
    @property
    def rhs(self):return self.fallback()[1]
    def multiply(self,xi):return product(self.matrix,xi,True,self.work)
    def residual(self,target,u):
        v=product(self.matrix,u,False,self.work)
        return [self.matrix.row(i).get(2*target+1,Q(0))-v[i] for i in range(self.r)]

    def labels(self,batch_width=32,broadcast=True,expected_epoch=None,gpu=None):
        if expected_epoch is not None and expected_epoch!=self.epoch:raise ValueError('stale epoch')
        labels={};proofs=[]
        if gpu is not None:
            from .compact_gpu import proposals
            labels,self.gpu_metadata=proposals(self,width=batch_width,**gpu)
        if len(labels)==self.n:return [labels[i] for i in range(self.n)],proofs
        with NativeAuxiliary(*self.fallback(),self.work) as native:
            for i in range(self.n):
                if i in labels:continue
                objective=[self.matrix.row(j).get(2*i+1,Q(0)) for j in range(self.r)]
                result=native.solve(objective);self.calls+=1;y=self.witness(result['x'])
                if result['status']=='optimal':check(self.a,self.rhs,objective,result)
                elif result['status']!='feasible_target' or result['value']<Q(1,4) or y[2*i+1]!=result['value']:
                    raise ArithmeticError('invalid compact CPU target')
                established={}
                for j in (range(self.n) if broadcast else (i,)):
                    if y[2*j+1]>=Q(1,4):established[j]=1
                    elif broadcast and self.broadcast_negative and y[2*j]>=Q(1,4):established[j]=-1
                established[i]=1 if result['value']>=Q(1,4) else -1
                if any(j in labels and labels[j]!=v for j,v in established.items()):raise ArithmeticError('label contradiction')
                labels.update(established);proofs.append(dict(target=i,certificate=result,established=established))
        return [labels[i] for i in range(self.n)],proofs
