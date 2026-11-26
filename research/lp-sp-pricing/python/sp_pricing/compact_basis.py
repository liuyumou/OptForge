"""Sparse exact rows and an implicit orthogonal complement; no dense null space."""
from collections import OrderedDict
from fractions import Fraction as Q
import threading

import numpy as np

from .exact import Limit, rational
from .gpu_wave import enclosure


class Storage:
    def __init__(self, entries=2_000_000, bytes_limit=4 << 30):
        self.entries = entries; self.bytes_limit = bytes_limit
        self.peak_entries = 0; self.peak_bytes = 0
        self.current={}; self.count=0; self.size=0

    def reset(self): self.current={}; self.count=0; self.size=0

    def observe(self, row):
        previous=self.current.get(id(row),(0,0))
        now=(len(row),sum(112+(abs(q.numerator).bit_length()+q.denominator.bit_length()+7)//8 for q in row.values()))
        self.current[id(row)]=now; self.count+=now[0]-previous[0]; self.size+=now[1]-previous[1]
        self.peak_entries=max(self.peak_entries,self.count); self.peak_bytes=max(self.peak_bytes,self.size)
        if self.count>self.entries or self.size>self.bytes_limit:raise Limit('compact_exact_storage_limit')

    def check(self, rows):
        count = sum(len(row) for row in rows)
        size = sum(112 + (abs(q.numerator).bit_length()+q.denominator.bit_length()+7)//8
                   for row in rows for q in row.values())
        self.peak_entries = max(self.peak_entries, count)
        self.peak_bytes = max(self.peak_bytes, size)
        if count > self.entries or size > self.bytes_limit:
            raise Limit('compact_exact_storage_limit')


class Rows:
    def __init__(self, rows, columns):
        self.rows = tuple({int(j): rational(v) for j, v in row.items() if v} for row in rows)
        self.r, self.s = len(self.rows), columns
        if self.s < 1 or any(j < 0 or j >= self.s for row in self.rows for j in row):
            raise ValueError('sparse row dimension')

    @classmethod
    def dense(cls, rows):
        if not rows or not rows[0] or any(len(r) != len(rows[0]) for r in rows):
            raise ValueError('matrix shape')
        return cls(({j: v for j, v in enumerate(row) if v} for row in rows), len(rows[0]))

    def __len__(self): return self.r
    def row(self, i): return self.rows[i]
    def column(self, j): return {i: row[j] for i, row in enumerate(self.rows) if j in row}
    @property
    def stored_entries(self): return sum(map(len, self.rows))


def sparse_rref(rows, columns, work, storage, coefficient_columns=None):
    """Incremental exact Gauss-Jordan; fill is checked before retaining each row."""
    limit = columns if coefficient_columns is None else coefficient_columns
    pivots = {}; incidence={}; storage.reset()
    tail = []
    for original in rows:
        work.tick()
        row = {j: rational(v) for j, v in original.items() if v}
        if any(j < 0 or j >= columns for j in row): raise ValueError('elimination dimension')
        for pivot in sorted(set(row).intersection(pivots)):
            factor = row.get(pivot)
            if not factor: continue
            for j, value in pivots[pivot].items():
                new = row.get(j, Q(0)) - factor*value
                if new: row[j] = new
                else: row.pop(j, None)
                work.tick(new, count=2)
        candidates = [j for j in row if j < limit]
        if not candidates:
            if row: tail.append(row)
            if row:storage.observe(row)
            continue
        pivot = min(candidates); scale = row[pivot]
        row = {j: v/scale for j, v in row.items()}
        work.tick(*row.values(), count=len(row))
        for old_pivot in list(incidence.get(pivot, ())):
            previous=pivots[old_pivot]
            factor = previous.get(pivot)
            if not factor: continue
            for j, value in row.items():
                new = previous.get(j, Q(0)) - factor*value
                if new:
                    previous[j] = new; incidence.setdefault(j,set()).add(old_pivot)
                else:
                    previous.pop(j, None); incidence.get(j,set()).discard(old_pivot)
                work.tick(new, count=2)
            storage.observe(previous)
        pivots[pivot] = row
        for j in row:incidence.setdefault(j,set()).add(pivot)
        storage.observe(row)
    order = sorted(pivots)
    return Rows([pivots[p] for p in order]+tail, columns), order


class NullRows:
    """If C=[I R] in pivot order, generate [-R^T I] one row at a time."""
    def __init__(self, positive, pivots):
        self.positive, self.pivots = positive, tuple(pivots)
        if positive.r != len(pivots): raise ValueError('basis rank')
        used = set(pivots)
        self.free = tuple(j for j in range(positive.s) if j not in used)
        self.r, self.s = len(self.free), positive.s
        # References to the same immutable rational coefficients; no negated
        # complement values and no zero/identity arrays are retained.
        self.factor_columns = {}
        for i in range(positive.r):
            for j, q in positive.row(i).items():
                if j not in used: self.factor_columns.setdefault(j, []).append((i, q))

    def row(self, i):
        j = self.free[i]
        return {j: Q(1), **{self.pivots[k]: -v for k, v in self.factor_columns.get(j, [])}}

    def column(self, j):
        if j in self.pivots:
            k = self.pivots.index(j)
            return {i: -self.positive.row(k)[f] for i, f in enumerate(self.free) if f in self.positive.row(k)}
        return {self.free.index(j): Q(1)}

    @property
    def stored_entries(self): return 0


class PairedRows:
    def __init__(self, positive, pivots):
        self.positive = positive; self.negative = NullRows(positive, pivots)
        self.r, self.s = positive.s, 2*positive.s

    def row(self, i):
        if i < self.positive.r:
            return {2*j+1: q for j, q in self.positive.row(i).items()}
        return {2*j: q for j, q in self.negative.row(i-self.positive.r).items()}

    @property
    def stored_entries(self): return self.positive.stored_entries


def product(matrix, vector, transpose=False, work=None):
    if len(vector) != (matrix.r if transpose else matrix.s): raise ValueError('product dimension')
    result = [Q(0)]*(matrix.s if transpose else matrix.r)
    for i in range(matrix.r):
        row = matrix.row(i)
        if transpose:
            if vector[i]:
                for j, q in row.items(): result[j] += q*vector[i]
        else:
            result[i] = sum((q*vector[j] for j, q in row.items() if vector[j]), Q(0))
        if work: work.tick(*([result[i]] if not transpose else []), count=2*len(row))
    return result


class TileSource:
    """Immutable tiles with bounded shared LRU; the basis is never densified."""
    def __init__(self, matrix, tile_rows=128, tile_columns=256, cache_bytes=32 << 20):
        if not 1 <= tile_rows <= 256 or not 1 <= tile_columns <= 512 or cache_bytes < 0:
            raise ValueError('tile bounds')
        self.matrix=matrix; self.r=matrix.r; self.s=matrix.s
        self.tr=tile_rows; self.tc=tile_columns; self.limit=cache_bytes
        self.cache=OrderedDict(); self.cache_bytes=0; self.peak_bytes=0
        self.lock=threading.RLock(); self.conversions=0; self.hits=0
        self.scalar_cache={Q(0):(0.,0.,0.)}
        self.descriptors=[]; self.nnz=0
        self.row_sums=np.zeros(self.r); self.column_sums=np.zeros(self.s)
        for begin in range(0, self.r, self.tr):
            columns=set()
            for i in range(begin, min(begin+self.tr, self.r)):
                for j, q in matrix.row(i).items():
                    v=abs(float(q))
                    if not np.isfinite(v): raise Limit('compact_float_range')
                    self.row_sums[i]+=v; self.column_sums[j]+=v
                    columns.add(j//self.tc); self.nnz+=1
            self.descriptors.extend((begin,j*self.tc) for j in sorted(columns))
        self.tau=np.divide(.9,self.row_sums,out=np.ones(self.r),where=self.row_sums>0)
        self.sigma=np.divide(.9,self.column_sums,out=np.ones(self.s),where=self.column_sums>0)
        if not np.isfinite(self.tau).all() or not np.isfinite(self.sigma).all(): raise Limit('compact_step_range')

    def tile(self, key):
        with self.lock:
            if key in self.cache:
                self.hits+=1; self.cache.move_to_end(key); return self.cache[key]
            i0,j0=key; nr=min(self.tr,self.r-i0); nc=min(self.tc,self.s-j0)
            result=np.zeros((3,nr,nc),dtype=np.float64)
            for i in range(nr):
                for j,q in self.matrix.row(i0+i).items():
                    if not j0<=j<j0+nc: continue
                    triple=self.scalar_cache.get(q)
                    if triple is None:
                        lo,hi=enclosure(q); triple=(float(q),lo,hi); self.conversions+=1
                        if len(self.scalar_cache)>=4096:self.scalar_cache.clear()
                        self.scalar_cache[q]=triple
                    result[:,i,j-j0]=triple
            result.flags.writeable=False
            while self.cache and self.cache_bytes+result.nbytes>self.limit:
                _, old=self.cache.popitem(last=False); self.cache_bytes-=old.nbytes
            if result.nbytes<=self.limit:
                self.cache[key]=result; self.cache_bytes+=result.nbytes
            self.peak_bytes=max(self.peak_bytes,self.cache_bytes)
            return result

    def objectives(self, slots):
        result=np.zeros((len(slots),self.r),dtype=np.float64)
        positions={}
        for q,j in enumerate(slots):positions.setdefault(j,[]).append(q)
        for i in range(self.r):
            row=self.matrix.row(i)
            if len(row)<len(slots):
                for j,value in row.items():
                    for q in positions.get(j,()):result[q,i]=float(value)
            else:
                for q,j in enumerate(slots): result[q,i]=float(row.get(j,0))
        return result
