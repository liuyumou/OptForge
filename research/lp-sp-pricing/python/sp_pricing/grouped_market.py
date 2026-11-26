"""Implicit expert cells and recursive wealth for Sections 6.3--6.6.

Demand guesses are never enumerated. Each group has four slot guesses and at
most one pivot guess. Difference-bound cells carry the wealth of every active
ancestor, so child refinements preserve the parent's retained investment.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
import itertools
import math
from .exact import Limit, dot
from .cells import canonical, count_and_moments
from .ellipsoid import Polytope, lex_minimize_lattice
from .market import median
from .recursive import parameters


@dataclass(frozen=True)
class Group:
    slots: tuple
    pivot: object = None  # (history level, signed coordinate slot)

    @property
    def dimension(self):
        return 4+int(self.pivot is not None)


@dataclass
class Cell:
    constraints: tuple
    wealth: list


class Cells:
    def __init__(self, bound, work, limit=200000):
        self.bound, self.work, self.limit = bound, work, limit
        self.cache = {}

    def moments(self, dimension, constraints):
        normalized = canonical(constraints)
        if normalized is None:
            return dict(count=0, sums=[0]*dimension)
        key = dimension, tuple(normalized)
        if key in self.cache:
            self.work.tick()
            return self.cache[key]
        if len(self.cache)>=self.limit:
            raise Limit("grouped_cell_cache_limit")
        # Difference-bound closure detects empty cells and fixed coordinates.
        size=dimension+1; zero=dimension
        distance=[[0 if i==j else 2*self.bound for j in range(size)] for i in range(size)]
        for i in range(dimension):
            distance[i][zero]=distance[zero][i]=self.bound
        for i,j,c in normalized:
            i=zero if i<0 else i;j=zero if j<0 else j
            distance[i][j]=min(distance[i][j],c)
        for k in range(size):
            for i in range(size):
                for j in range(size):
                    distance[i][j]=min(distance[i][j],distance[i][k]+distance[k][j])
            self.work.tick(count=size*size)
        if any(distance[i][i]<0 for i in range(size)):
            answer=dict(count=0,sums=[0]*dimension)
        else:
            fixed={i:distance[i][zero] for i in range(dimension)
                   if distance[i][zero]==-distance[zero][i]}
            if fixed:
                remaining=[i for i in range(dimension) if i not in fixed]
                mapping={i:j for j,i in enumerate(remaining)}
                reduced=[]
                for i,j,c in normalized:
                    reduced.append((mapping.get(i,-1),mapping.get(j,-1),c-fixed.get(i,0)+fixed.get(j,0)))
                for i in remaining:
                    reduced += [(mapping[i],-1,distance[i][zero]),(-1,mapping[i],distance[zero][i])]
                rest=self.moments(len(remaining),reduced)
                answer=dict(count=rest["count"],sums=[fixed[i]*rest["count"] if i in fixed else rest["sums"][mapping[i]] for i in range(dimension)])
            else:
                answer=count_and_moments(dimension,self.bound,normalized,self.work)
        self.cache[key]=answer
        return answer

    def split(self, cell, dimension, i, j, threshold):
        threshold=Q(threshold)
        low=math.ceil(threshold)-1; high=math.floor(threshold)+1
        branches=[((i,j,low),),((j,i,-high),)]
        if threshold.denominator==1:
            branches.insert(1,((i,j,int(threshold)),(j,i,-int(threshold))))
        result=[]
        for branch in branches:
            normalized=canonical([*cell.constraints,*branch])
            if normalized is None:
                continue
            constraints=tuple(normalized)
            if self.moments(dimension,constraints)["count"]:
                result.append(Cell(constraints,cell.wealth[:]))
        return result

    def refine(self, group, cells, prices, history):
        if group.pivot is not None and group.pivot[0]>=len(history):
            return cells
        # Utility k is guess_k-guess_pivot+offset_k. Outside is zero.
        offsets=[-h*prices[i] for i,h in group.slots]
        pivot=-1
        if group.pivot is not None:
            level,(i,h)=group.pivot
            pivot=4
            offsets=[v+h*history[level][i] for v in offsets]
        comparisons=[(k,pivot,-offsets[k]) for k in range(4)]
        comparisons += [(i,j,offsets[j]-offsets[i]) for i in range(4) for j in range(i+1,4)]
        result=cells
        for i,j,threshold in comparisons:
            result=[child for cell in result for child in self.split(cell,group.dimension,i,j,threshold)]
            if len(result)>self.limit:
                raise Limit("grouped_cell_refinement_limit")
        return result


def utilities(group, guesses, prices, history):
    if group.pivot is not None and group.pivot[0]>=len(history):
        return [Q(0)]
    threshold=Q(0)
    if group.pivot is not None:
        level,(i,h)=group.pivot
        threshold=guesses[4]-h*history[level][i]
    return [Q(0)]+[guesses[k]-threshold-h*prices[i] for k,(i,h) in enumerate(group.slots)]


class GroupedMarket:
    def __init__(self, n, bound, depth, work, group_limit=100000, cell_limit=200000):
        count=(2*n)**4*(1+depth*2*n)
        if count>group_limit:
            raise Limit("implicit_market_group_limit")
        self.n,self.bound,self.depth,self.work=n,bound,depth,work
        self.cells=Cells(bound,work,cell_limit)
        slots=tuple((i,h) for i in range(n) for h in (-1,1))
        pivots=(None,)+tuple((level,slot) for level in range(depth) for slot in slots)
        self.groups={Group(tuple(chosen),pivot):[Cell((),[Q(1)])]
                     for chosen in itertools.product(slots,repeat=4) for pivot in pivots}

    def total(self):
        return sum((self.cells.moments(group.dimension,cell.constraints)["count"]*cell.wealth[-1]
                    for group,cells in self.groups.items() for cell in cells),Q(0))

    def evaluate(self, prices, history, permanent=False):
        gradient=[Q(0)]*self.n;intercept=Q(0)
        for group,cells in list(self.groups.items()):
            refined=self.cells.refine(group,cells,prices,history)
            if permanent:
                self.groups[group]=refined
            for cell in refined:
                moment=self.cells.moments(group.dimension,cell.constraints)
                count=moment["count"]
                if not count:
                    continue
                guesses=[Q(v,count) for v in moment["sums"]]
                options=utilities(group,guesses,prices,history)
                first=options.index(max(options))
                if first:
                    k=first-1;i,h=group.slots[k]
                    constant=Q(moment["sums"][k])
                    if group.pivot is not None:
                        level,(pivot_i,pivot_h)=group.pivot
                        constant-=moment["sums"][4]
                        constant+=count*pivot_h*history[level][pivot_i]
                    weight=cell.wealth[-1]
                    intercept+=weight*constant;gradient[i]-=weight*count*h
                    self.work.tick(intercept,gradient[i])
        return dot(gradient,prices,self.work)+intercept,gradient,intercept

    def propose(self, history):
        total=self.total()
        denominator=2*math.lcm(*(cell.wealth[-1].denominator for cells in self.groups.values() for cell in cells))
        history_bound=max((abs(v) for p in history for v in p),default=Q(0))
        price_bound=2*self.bound+math.ceil(history_bound)+1
        height_bound=math.ceil(2*total*price_bound)+1
        coefficient_bound=max(denominator,math.ceil(denominator*total))
        def separate(point,delta):
            prices,height=point[:-1],point[-1]
            for i,p in enumerate(prices):
                if abs(p)>price_bound+delta:
                    return [(1 if p>0 else -1)*int(j==i) for j in range(self.n+1)],price_bound
            if height < -delta:
                return [0]*self.n+[-1],0
            value,gradient,intercept=self.evaluate(prices,history)
            if denominator*(value-height)>delta:
                scaled=[v*denominator for v in gradient]
                rhs=-intercept*denominator
                if any(v.denominator!=1 for v in [*scaled,rhs]):
                    raise ArithmeticError("market common denominator")
                return [int(v) for v in scaled]+[-denominator],int(rhs)
            return None
        poly=Polytope(self.n+1,max(price_bound,height_bound),coefficient_bound,separate)
        result=lex_minimize_lattice(poly,self.work,[2]*self.n+[denominator],[self.n,*range(self.n)])
        if result["status"]!="optimal":
            raise ArithmeticError("bounded market must have an optimum")
        prices=result["x"][:-1]
        value,_,_=self.evaluate(prices,history,permanent=True)
        if value!=result["x"][-1] or any(v.denominator not in (1,2) for v in prices):
            raise ArithmeticError("market vertex postcondition")
        return prices

    def split_wealth(self):
        for cells in self.groups.values():
            for cell in cells:
                wealth=cell.wealth[-1]
                cell.wealth[-1]=wealth*Q(16383,16384)
                cell.wealth.append(wealth/Q(16384))

    def recombine(self, history, prices, feedback):
        for group,cells in self.groups.items():
            for cell in cells:
                moment=self.cells.moments(group.dimension,cell.constraints)
                guesses=[Q(v,moment["count"]) for v in moment["sums"]]
                values=utilities(group,guesses,prices,history);top=max(values)
                gains=([0] if values[0]==top else [])
                gains += [h*feedback[i] for (i,h),v in zip(group.slots,values[1:]) if v==top]
                returned=cell.wealth.pop()
                cell.wealth[-1]=cell.wealth[-1]*(1+Q(min(gains),16))+returned
                self.work.tick(cell.wealth[-1])


def grouped_search(n,bound,labels,work,query_limit=1024,component_parameters=None,market_factory=GroupedMarket):
    settings=parameters(n,bound)
    if component_parameters is not None:
        settings=dict(settings,**component_parameters)
    elif settings["leaf_probes"]>query_limit:
        raise Limit("literal_tree_query_admission")
    market=market_factory(n,bound,settings["depth"],work)
    queries=0
    def node(history):
        nonlocal queries
        if len(history)==settings["depth"]:
            return median(history)
        before=market.total();children=[]
        probes=settings["branching"] if history else settings["root_branching"]
        for _ in range(probes):
            prices=market.propose(history)
            market.split_wealth();returned=node(history+[prices])
            if queries>=query_limit:
                raise Limit("literal_recursive_query_limit")
            signs=labels(returned);queries+=1
            feedback=[signs[i] if returned[i]==prices[i] else (1 if returned[i]>prices[i] else -1) for i in range(n)]
            market.recombine(history,prices,feedback);children.append(returned)
            if market.total()>before:
                raise ArithmeticError("grouped recursive wealth increased")
        return median(children)
    return dict(prices=node([]),queries=queries,paper_constants=component_parameters is None)
