"""Development-only LP conversion from the retained HiGHS source distribution.

This strict converter rejects unsupported sections, integer columns, alternate
RHS/range/bound sets and quadratic data. It is evaluation tooling, not a reader
in the solver runtime. Native HiGHS roundtrip is a separate admission check.
"""
import math
from pathlib import Path
from lp_general_common import BASE,ROOT,put,ref,require

SOURCE=ROOT/'target/native/highs-1.11.0/HiGHS-1.11.0'
NAMES=('afiro','adlittle','israel','25fv47')

def parse(path):
    rows={};columns={};rhs={};ranges={};bounds={};sets={};section=None;objective=None;sense='minimize'
    for raw in Path(path).read_text().splitlines():
        if not raw.strip() or raw.startswith('*'):continue
        t=raw.split()
        if not raw[0].isspace():
            section=t[0];require(section in ('NAME','OBJSENSE','ROWS','COLUMNS','RHS','RANGES','BOUNDS','ENDATA'),'unsupported MPS section '+section)
            continue
        if section=='OBJSENSE':
            require(t[0].upper() in ('MIN','MAX'),'objective sense');sense='minimize' if t[0].upper()=='MIN' else 'maximize'
        elif section=='ROWS':
            require(len(t)==2 and t[0] in ('N','L','E','G') and t[1] not in rows,'row declaration')
            if t[0]=='N':require(objective is None,'multiple free rows');objective=t[1]
            rows[t[1]]=t[0]
        elif section in ('COLUMNS','RHS','RANGES'):
            require(len(t) in (3,5) and 'MARKER' not in raw,'unsupported integer/entry data')
            name=t[0]
            if section=='COLUMNS':dest=columns.setdefault(name,{})
            else:
                require(sets.setdefault(section,name)==name,'multiple MPS sets');dest=rhs if section=='RHS' else ranges
            for r,v in zip(t[1::2],t[2::2]):
                value=float(v.replace('D','E'));require(r in rows and math.isfinite(value),'MPS coefficient')
                if section=='COLUMNS':dest[r]=dest.get(r,0.)+value
                else:require(r not in dest,'duplicate RHS/range');dest[r]=value
        elif section=='BOUNDS':
            require(len(t) in (3,4),'bound fields');kind,name,col=t[:3]
            require(sets.setdefault(section,name)==name and col in columns,'bound set/column')
            lo,hi=bounds.get(col,(0.,None));v=float(t[3]) if len(t)==4 else None
            require(v is None or math.isfinite(v),'bound value')
            if kind=='LO' and v is not None:lo=v
            elif kind=='UP' and v is not None:hi=v
            elif kind=='FX' and v is not None:lo=hi=v
            elif kind=='FR' and v is None:lo=hi=None
            elif kind=='MI' and v is None:lo=None
            elif kind=='PL' and v is None:hi=None
            else:raise ValueError('unsupported bound '+kind)
            bounds[col]=(lo,hi)
        else:raise ValueError('data outside supported MPS section')
    require(objective is not None and section=='ENDATA','incomplete MPS')
    b=lambda v,side:dict(kind='finite',value=v) if v is not None else dict(kind=side+'_infinity')
    ids={c:3*j+7 for j,c in enumerate(columns)};row_names=[r for r in rows if r!=objective]
    constraints=[]
    for i,r in enumerate(row_names):
        value=rhs.get(r,0.);kind=rows[r];lo=value if kind in ('E','G') else None;hi=value if kind in ('E','L') else None
        if r in ranges:
            width=ranges[r]
            if kind=='L':lo=value-abs(width)
            elif kind=='G':hi=value+abs(width)
            elif width>=0:hi=value+width
            else:lo=value+width
        constraints.append(dict(id=5*i+11,lower=b(lo,'negative'),upper=b(hi,'positive'),
            terms=[dict(variable_id=ids[c],coefficient=v[r]) for c,v in columns.items() if v.get(r,0.)!=0]))
    doc=dict(schema_version=1,model_id='general-dev-public-'+Path(path).stem,
        variables=[dict(id=ids[c],domain='continuous',lower=b(bounds.get(c,(0.,None))[0],'negative'),upper=b(bounds.get(c,(0.,None))[1],'positive')) for c in columns],
        constraints=constraints,objective=dict(sense=sense,offset=-rhs.get(objective,0.),
            terms=[dict(variable_id=ids[c],coefficient=v[objective]) for c,v in columns.items() if v.get(objective,0.)!=0]))
    return doc,dict(columns=list(columns),rows=row_names,objective=objective)

def materialize():
    out=BASE/'public-development-v1';out.mkdir(parents=True,exist_ok=False);entries=[]
    for name in NAMES:
        source=SOURCE/'check/instances'/(name+'.mps');doc,names=parse(source)
        entries.append(dict(model=put(out/(name+'.json'),doc),source=ref(source),names=names,
            partition='development',source_group='HiGHS-1.11.0/check/instances',family='public-'+name))
    put(out/'manifest.json',dict(models=entries,converter=ref(__file__),distribution_license=ref(SOURCE/'LICENSE.txt'),
        source_distribution='https://github.com/ERGO-Code/HiGHS/tree/v1.11.0/check/instances',holdout_accessed=False))

if __name__=='__main__':materialize()
