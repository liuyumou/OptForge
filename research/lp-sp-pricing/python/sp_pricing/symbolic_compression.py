"""Online common-scale compression using only exact affine sign queries."""
from fractions import Fraction as Q
from dataclasses import dataclass
import math
from .compression import lll,bounded_power,Restart


@dataclass
class Form:
    constant: Q
    coefficients: dict

    @classmethod
    def scalar(cls,value):return cls(Q(value),{})
    @classmethod
    def variable(cls,index):return cls(Q(0),{index:Q(1)})
    def __add__(self,other):
        if not isinstance(other,Form):other=Form.scalar(other)
        coefficients=dict(self.coefficients)
        for index,value in other.coefficients.items():
            coefficients[index]=coefficients.get(index,Q(0))+value
            if not coefficients[index]:del coefficients[index]
        return Form(self.constant+other.constant,coefficients)
    def __neg__(self):return self.scale(-1)
    def __sub__(self,other):return self+-other if isinstance(other,Form) else self+(-Q(other))
    def scale(self,value):
        value=Q(value)
        return Form(self.constant*value,{i:c*value for i,c in self.coefficients.items() if c*value})


class SymbolicCompression:
    def __init__(self,sign,norm_bound,eta,dissociation_bound,work):
        self.oracle,self.M,self.eta,self.D,self.work=sign,norm_bound,Q(eta),dissociation_bound,work
        if self.M<1 or not 0<self.eta<1 or self.D<1:raise ValueError('compression parameters')
        self.indices=[];self.answers={};self.epoch=0;self.initialize()

    def sign(self,form):
        self.work.tick(form.constant,*form.coefficients.values(),count=len(form.coefficients)+1)
        return self.oracle(form.constant,form.coefficients)

    def absolute(self,form):return form.scale(-1) if self.sign(form)<0 else form

    def maximum(self,forms):
        answer=Form.scalar(0)
        for form in forms:
            value=self.absolute(form)
            if self.sign(value-answer)>0:answer=value
        return answer

    def floor_ratio(self,value,positive,low,high):
        if self.sign(value-positive.scale(low))<0 or self.sign(value-positive.scale(high))>=0:return None
        while high-low>1:
            middle=(low+high)//2
            if self.sign(value-positive.scale(middle))>=0:low=middle
            else:high=middle
        return low

    def initialize(self):
        m=len(self.indices);inverse=100*(m+1)*self.M
        self.C=int(self.work.power2(m*(m+1)))*bounded_power(2*inverse,m+1,self.work)
        self.H=100*self.M*self.C;self.base=10*self.M*(m*self.H+3)
        remainder=[Form.variable(i) for i in self.indices];self.expansion=[]
        while self.sign(self.maximum(remainder)-self.H)>0:
            if len(self.expansion)>=m:raise ArithmeticError('scale rank did not decrease')
            maximum=self.maximum(remainder);denominator=2*self.C*inverse
            approximation=[]
            for value in remainder:
                integer=self.floor_ratio(value.scale(denominator)+maximum.scale(Q(1,2)),maximum,
                                         -denominator-1,denominator+2)
                if integer is None:raise ArithmeticError('normalized scale coordinate')
                approximation.append(Q(integer,denominator))
            common=math.lcm(self.C,*(v.denominator for v in approximation))
            lattice=[[common*int(i==j) for j in range(m)]+[0] for i in range(m)]
            lattice.append([int(v*common) for v in approximation]+[common//self.C])
            short=lll(lattice,self.work)[0];q=Q(short[-1]*self.C,common)
            if q<0:q=-q;short=[-v for v in short]
            digits=[q*v-Q(s,common) for v,s in zip(approximation,short)]
            if q.denominator!=1 or not 1<=q<=self.C or any(z.denominator!=1 or abs(z)>q for z in digits):
                raise ArithmeticError('symbolic LLL postcondition')
            scale=maximum.scale(1/q)
            remainder=[v-scale.scale(z) for v,z in zip(remainder,digits)]
            if self.sign(self.maximum(remainder)-scale.scale(Q(1,inverse)))>0:
                raise ArithmeticError('symbolic common-scale error')
            self.expansion.append(dict(scale=scale,digits=list(map(int,digits))))
        self.answers={}

    def request(self,index):
        if index in self.answers:return self.answers[index]
        m=len(self.indices);residual=Form.variable(index);digits=[];valid=True
        for entry in self.expansion:
            scale=entry['scale'];bound=m*self.C
            digit=self.floor_ratio(residual+scale.scale(Q(1,2)),scale,-bound,bound+1)
            if digit is None:valid=False;break
            residual=residual-scale.scale(digit)
            if self.sign(self.absolute(residual)-scale.scale(Q(1,10*self.M)))>0:valid=False;break
            digits.append(digit)
        valid=valid and self.sign(self.absolute(residual)-(m*self.H+2))<=0
        if not valid:
            if index in self.indices or m+1>=self.D:raise ArithmeticError('dissociation promise violated')
            self.indices.append(index);self.epoch+=1;self.initialize();raise Restart(self.epoch)
        bound=math.ceil(Q(m*self.H+2)/self.eta)
        grid=self.floor_ratio(residual,Form.scalar(self.eta),-bound-1,bound+1)
        if grid is None:raise ArithmeticError('residual grid bound')
        answer=grid*self.eta
        for j,digit in enumerate(digits):answer+=digit*bounded_power(self.base,len(digits)-j,self.work)
        result=dict(value=answer,epoch=self.epoch,index=index)
        self.answers[index]=result;self.work.tick(answer)
        return result

    def validate_epoch(self,answer):
        if answer['epoch']!=self.epoch:raise ValueError('stale compression answer')


def uniform_parameters(d,k,work,dissociation=None):
    D=(d+1)**6 if dissociation is None else dissociation
    eta_bits=k+(4*D-1).bit_length();eta=work.power2(-eta_bits)
    A=int(work.power2(k))*(D+4)*eta.denominator
    M=(D+1)*bounded_power(A,D+1,work)
    m=D-1;inverse=100*(m+1)*M
    C=int(work.power2(m*(m+1)))*bounded_power(2*inverse,m+1,work)
    H=100*M*C;B=10*M*(m*H+3)
    U=bounded_power(B,m+2,work)*eta.denominator
    F=(D+2)*bounded_power(A*U+1,D+1,work)*U*eta.denominator
    # Overbound the common scale numerator/denominator (2C)^m, every
    # normalized grid, digit and residual query, and denominator clearing.
    query=1000*(D+1)**4*bounded_power(2*C,4*(D+1),work)*bounded_power(M+1,4,work)
    query*=bounded_power(eta.denominator,4,work)*bounded_power(H+1,4,work)
    T=int(work.power2((query*eta.denominator-1).bit_length()))
    work.tick(A,M,C,H,B,U,F,T)
    return dict(D=D,eta=eta,M=M,F=F,T=T,R=4*F,K=k)
