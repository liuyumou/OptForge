"""Portable integrity replay of chunked models, endpoints, sources and receipts."""
import argparse
import json
import os
import shutil
from pathlib import Path
from lp_billion_common import BASE, ROOT, digest, load, put, ref, require


def references(value):
    if isinstance(value, dict):
        if {'namespace','path','bytes','sha256'} <= value.keys():
            yield value
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def arrays(value):
    if isinstance(value, dict):
        if {'dtype','count','chunks'} <= value.keys():
            yield value
        for child in value.values():
            yield from arrays(child)
    elif isinstance(value, list):
        for child in value:
            yield from arrays(child)


def key(item):
    return item['namespace'], item['path'], item['bytes'], item['sha256']


def evidence_files(root, excluded, building=None):
    for directory, dirs, names in os.walk(root):
        relative = Path(directory).relative_to(root)
        if relative == Path('.'):
            dirs[:] = [n for n in dirs if n not in {'target','portable-view'}]
        if building is not None:
            dirs[:] = [n for n in dirs if Path(directory)/n != building]
        for name in names:
            path=Path(directory)/name
            if path.is_symlink() or (relative == Path('.') and name in {'budget.lock','cpu.lock'}):
                continue
            if relative == Path('resources') and any(name.startswith(i+'.') for i in excluded):
                continue
            yield path


def build(identity, excluded):
    require(identity and Path(identity).name==identity and identity not in ['.','..'],'portable identity')
    out=BASE/'portable'/identity;out.mkdir(parents=True,exist_ok=False)
    retained={}
    for manifest in (BASE/'sources').glob('*/manifest.json'):
        for pair in load(manifest)['sources']:
            retained[key(pair['original'])]=pair['retained']['path']
    documents=[]
    for p in evidence_files(BASE, excluded, out):
        if p.suffix=='.json':
            documents.append((p,load(p)))
    external={}
    position=0
    while position<len(documents):
        _,doc=documents[position];position+=1
        for item in references(doc):
            if item['namespace']!='repo':
                continue
            k=key(item)
            if k in external:
                continue
            if k in retained:
                destination=retained[k]
            else:
                source=(ROOT/item['path']).resolve()
                require(source.is_relative_to(ROOT) and ref(source)==item,'external source binding '+item['path'])
                target=BASE/'dependencies'/item['sha256']/Path(item['path']).name
                target.parent.mkdir(parents=True,exist_ok=True)
                if not target.exists():
                    shutil.copyfile(source,target)
                    if target.suffix=='.json':
                        documents.append((target,load(target)))
                destination=str(target.relative_to(BASE))
            external[k]=dict(original=item,portable_path=destination)
    entries=[]
    for p in sorted(evidence_files(BASE, excluded, out)):
        require(p.stat().st_size<512<<20,'individual evidence file ceiling '+str(p))
        entries.append(dict(path=str(p.relative_to(BASE)),bytes=p.stat().st_size,sha256=digest(p)))
    put(out/'manifest.json',dict(schema_version=1,identity=identity,entries=entries,
        external=list(external.values()),excluded_live_resources=excluded,
        excluded_reconstructible_build_cache='target',
        source='Direct content-addressed evidence; no second full-size archive.'))
    print(dict(files=len(entries),external_bindings=len(external),bytes=sum(e['bytes'] for e in entries)),flush=True)


def replay(root,manifest,output):
    root=root.resolve();catalog=load(manifest)
    entries={e['path']:e for e in catalog['entries']}
    require(len(entries)==len(catalog['entries']),'unique portable paths')
    for e in entries.values():
        p=(root/e['path']).resolve()
        require(p.is_relative_to(root) and p.is_file(),'portable containment')
        require(p.stat().st_size==e['bytes'],'portable bytes '+e['path'])
        if e['path'].startswith('objects/'):
            require(p.stem==e['sha256'],'content-addressed object filename')
    external={key(e['original']):e['portable_path'] for e in catalog['external']}
    bindings=vector_refs=responses=assessments=0
    endpoints=set()
    for name in entries:
        if not name.endswith('.json'):
            continue
        doc=load(root/name)
        for item in references(doc):
            path=item['path'] if item['namespace']=='evidence' else external[key(item)]
            require(path in entries,'referenced portable file '+path)
            e=entries[path]
            require((e['bytes'],e['sha256'])==(item['bytes'],item['sha256']),'portable reference binding')
            bindings+=1
        for a in arrays(doc):
            width={'u32le':4,'u64le':8,'f64le':8}[a['dtype']]
            require(sum(c['bytes'] for c in a['chunks'])==width*a['count'],'array byte length')
            for c in a['chunks']:
                e=entries['objects/'+c['sha256']+'.bin']
                require((e['bytes'],e['sha256'])==(c['bytes'],c['sha256']),'array object binding')
                require(c['bytes']<=32<<20 and c['bytes']%width==0,'canonical chunk domain')
            vector_refs+=1
        if isinstance(doc,dict) and doc.get('kind')=='general-lowbit-solve' and 'endpoint' in doc:
            responses+=1
            for e in [*doc['assessments'],doc]:
                require(e['endpoint']['primal']['count']==doc['columns'] and
                        e['endpoint']['dual']['count']==doc['rows'],'endpoint dimensions')
                assessments+=1
                endpoints.add(json.dumps(e['endpoint'],sort_keys=True))
    # Validate the complete reference graph before streaming the large payload.
    for e in entries.values():
        require(digest(root/e['path'])==e['sha256'],'portable bytes '+e['path'])
    result=dict(status='passed',manifest_sha256=digest(manifest),files=len(entries),
        file_bytes=sum(e['bytes'] for e in entries.values()),reference_bindings=bindings,
        array_references=vector_refs,response_records=responses,assessment_records=assessments,
        distinct_endpoints=len(endpoints),original_repository_access_required=False,
        scope='Integrity replay; numerical serial comparisons are separately source-bound audit receipts.')
    with output.open('x') as stream:
        json.dump(result,stream,sort_keys=True,indent=2,allow_nan=False)
        stream.write('\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    b=sub.add_parser('build');b.add_argument('--id',required=True);b.add_argument('--exclude-resource',action='append',default=[])
    r=sub.add_parser('replay');r.add_argument('root',type=Path);r.add_argument('manifest',type=Path);r.add_argument('output',type=Path)
    a=p.parse_args()
    if a.action=='build':build(a.id,a.exclude_resource)
    else:replay(a.root,a.manifest,a.output)
