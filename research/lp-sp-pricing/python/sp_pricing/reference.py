"""Literal Sections 3--6 integration with explicit resource admission.

The enormous paper constants are preserved. A refusal before allocation is an
incomplete run, never a solved LP. Small-parameter component tests do not acquire
the paper's complexity or visibility guarantees.
"""
from fractions import Fraction as Q
import math
from .exact import Limit,determinant_newton,rational,basis,nullspace
from .compression import Restart
from .symbolic_compression import SymbolicCompression,uniform_parameters
from .log_oracle import LogOracle
from .calibration import paper_bounds
from .geometry import paired_space,slack_space,restrict_space,LabelOracle,recover_slack_certificate
from .ellipsoid import explicit,feasible
from .grouped_market import grouped_search


def exp2_small(exponent,bits,work):
    """Section 4.4 rational approximation, absolute error below 2^-bits."""
    exponent=Q(exponent)
    if exponent>0:raise ValueError('normalized exponent must be nonpositive')
    if exponent < -bits:return Q(0)
    integer=math.floor(exponent);fraction=exponent-integer
    if not fraction:return work.power2(integer)
    length=bits+10
    logarithm=sum((Q(1,j*2**j) for j in range(1,length+1)),Q(0))
    argument=fraction*logarithm;term=Q(1);value=Q(1)
    for j in range(1,length+1):
        term*=argument/j;value+=term;work.tick(term,value)
    return value*work.power2(integer)


class CompressedCalibration:
    def __init__(self,original,work,*,component_precision=None,component_parameters=None):
        self.original=[list(map(rational,row)) for row in original]
        self.n=len(original[0])//2;self.rank=len(original);self.work=work
        if len(original[0])!=2*self.n or any(len(row)!=2*self.n for row in original):raise ValueError('paired basis')
        self.precision=10000*self.n*self.n if component_precision is None else component_precision
        self.paper_constants=component_precision is None and component_parameters is None
        forecast=paper_bounds(self.n)
        if self.paper_constants and forecast['demand_bound_bits_upper']>work.max_bits:
            raise Limit('literal_parameter_bit_admission')
        self.E=self.precision+6;self.minors={}
        A=(self.E+5)*int(work.power2(self.E))
        # K is the least integer with 2^K >= (N+1)*A^(N+1).
        from .compression import bounded_power
        k=((self.n+1)*bounded_power(A,self.n+1,work)-1).bit_length()
        params=uniform_parameters(2*self.n,k,work) if component_parameters is None else component_parameters
        self.parameters=params;self.demand_bound=params['R']
        self.logs=LogOracle(self.minor,params['eta'],params['T'],work)
        self.compression=SymbolicCompression(self.logs.sign,params['M'],params['eta'],params['D'],work)

    @property
    def epoch(self):return self.compression.epoch

    def minor(self,index):
        rows,columns=index
        if index not in self.minors:
            self.minors[index]=determinant_newton([[self.original[i][j] for j in columns] for i in rows],self.work)
        return self.minors[index]

    def query(self,prices):
        if len(prices)!=self.n or any(Q(p).denominator not in (1,2) for p in prices):raise ValueError('half-integral prices')
        pivots=[];rows=[];previous=Q(1)
        for j in range(self.rank):
            cofactors=[];scores={}
            for s in range(2*self.n):
                index=(tuple(range(j+1)),tuple(pivots+[s]))
                value=Q(0) if s in pivots else self.minor(index);cofactors.append(value)
                if value:
                    proxy=self.compression.request(index)['value']
                    scores[s]=proxy-(1 if s%2 else -1)*prices[s//2]
            if not scores:raise ValueError('dependent ordered basis')
            pivot=max(scores,key=lambda s:(scores[s],-s))
            row=[Q(0)]*(2*self.n)
            for s,score in scores.items():
                row[s]=(1 if previous*cofactors[s]>0 else -1)*exp2_small(score-scores[pivot],self.E,self.work)
            rows.append(row);pivots.append(pivot);previous=cofactors[pivot]
        h=self.work.power2(100*self.n*self.n)
        return dict(basis=rows,pivots=pivots,H=h,epsilon=h**-10,epoch=self.epoch,
                    precision_bits=self.precision,paper_constants=self.paper_constants,
                    calibration='online_minor_log_compression',entry_error=self.work.power2(-self.precision))


def ellipsoid_labels(oracle,gpu=None,batch_width=32):
    labels={};proofs=[]
    if gpu is not None:
        from .gpu import propose_labels
        labels,proofs,metadata=propose_labels(oracle,width=batch_width,**gpu)
    else:metadata=None
    for i in range(oracle.n):
        if i in labels:continue
        a=oracle.a+[[-v for v in oracle.columns[2*i+1]]]
        b=oracle.rhs+[Q(-1,4)]
        result=feasible(explicit(a,b,math.ceil(oracle.h)),oracle.work)
        labels[i]=1 if result['feasible'] else -1
        proofs.append(dict(target=i,label=labels[i],decision=result,epoch=oracle.epoch,
                           oracle='rational_rounded_ellipsoid'))
    return [labels[i] for i in range(oracle.n)],proofs,metadata


def recover_circuit(original,target,decide,work,dimension):
    signs=decide(original,dimension);side=signs[target]
    selected=basis(original,work) if side==1 else nullspace(original,work,dimension)
    zeros=[]
    for j in range(dimension):
        if j==target:continue
        # Always rebuild from the selected original input, never a chain of
        # successively rounded/transformed coefficient matrices.
        candidate=restrict_space(selected,zeros+[j],work,dimension)
        if decide(candidate,dimension)[target]==1:zeros.append(j)
    final=restrict_space(selected,zeros,work,dimension)
    if len(final)!=1 or final[0][target]==0:raise ArithmeticError('circuit recovery did not isolate a line')
    vector=[v/final[0][target] for v in final[0]]
    if any(v<0 for v in vector):raise ArithmeticError('recovered circuit is not nonnegative')
    return side,vector


def solve_reference(owner,model,mode):
    from .solver import PricingSolver
    class ReferencePricingSolver(PricingSolver):
        literal_reference=True
        def decide(self,c,n):
            with self.phase('geometry_and_compression'):
                calibration=CompressedCalibration(paired_space(c,self.work,n),self.work)
            while True:
                def labels(prices):
                    with self.phase('calibration'):
                        calibrated=calibration.query(prices)
                        oracle=LabelOracle(calibrated['basis'],calibrated['H'],calibrated['epsilon'],self.work,calibration.epoch)
                    with self.phase('auxiliary_labels'):
                        signs,proofs,gpu_meta=ellipsoid_labels(oracle,self.gpu if mode=='certified_acceleration' else None,self.batch_width)
                    self.queries+=1
                    self.events.append(dict(query=self.queries,epoch=calibration.epoch,prices=prices,labels=signs,
                        calibration=calibrated,label_proofs=proofs,gpu=gpu_meta))
                    return signs
                try:
                    with self.phase('implicit_recursive_search'):
                        result=grouped_search(n,calibration.demand_bound,labels,self.work,
                                              query_limit=self.max_queries-self.queries)
                    if any(v==0 for v in result['prices']):raise ArithmeticError('literal final price is zero')
                    return [1 if v>0 else -1 for v in result['prices']]
                except Restart:
                    self.events.append(dict(kind='compression_restart',epoch=calibration.epoch,
                                            all_previous_prices_and_wealth_discarded=True))

        def feasibility(self,a,b,columns):
            n=len(b)+1
            if (len(b)+1)*(columns+1)>100000 or 2*n*n>1000000:raise Limit('reference_geometry_capacity')
            c=slack_space(a,b,self.work,columns)
            side,vector=recover_circuit(c,n-1,self.decide,self.work,n)
            return recover_slack_certificate(a,b,side,vector,self.work,columns)

        def result(self,proof):
            return dict(status='certificate_returned',certificate=proof,mode=mode,
                paper_algorithm_completed=True,implementation_complete=True,
                calibration='online_minor_log_compression',search='implicit_recursive_expert_cells',
                cpu_oracle='rational_rounded_ellipsoid',queries=self.queries,events=self.events,
                strongly_polynomial_claim=False,
                complexity_note='reference structure implemented; no empirical validation of a complete literal run',
                gpu_work=mode=='certified_acceleration' and self.gpu is not None)
    forecast=paper_bounds(len(model['b'])+1)
    if forecast['demand_bound_bits_upper']>owner.work.max_bits:
        return dict(status='resource_limit',reason='literal_parameter_bit_admission',parameter_forecast=forecast,
                    certificate=None,mode=mode,paper_algorithm_completed=False,implementation_complete=True,
                    strongly_polynomial_claim=False)
    delegate=ReferencePricingSolver(owner.work,owner.extra_experts,owner.max_queries,owner.batch_width,owner.seed,owner.gpu,owner.market_backend)
    delegate.events=owner.events;delegate.phase_ns=owner.phase_ns
    try:return PricingSolver.solve(delegate,model,'practical')
    finally:owner.queries=delegate.queries
