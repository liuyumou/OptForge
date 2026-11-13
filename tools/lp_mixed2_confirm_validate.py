"""Prospective roster and fail-closed analysis admission on non-scientific records."""
import copy
import hashlib
import json
import tempfile
import gzip
import io
import tarfile
from pathlib import Path
from lp_mixed2_confirm_common import BASE, PRIOR, ROOT, load, put, ref, require
from lp_mixed2_confirm_confirmation import roster
from lp_mixed2_confirm_analysis import assess, DiskRecords, PartWriter, PartReader


def main():
    with tempfile.TemporaryDirectory(dir=BASE,prefix='part-admission-') as directory:
        payload=bytes(range(256))*7
        with PartWriter('bounded',Path(directory),limit=97) as writer:
            for offset in range(0,len(payload),113):writer.write(payload[offset:offset+113])
        index=writer.index()
        require(b''.join((ROOT/p['path']).read_bytes() for p in index['parts'])==payload,'part roundtrip')
        require(index['bytes']==len(payload) and index['sha256']==hashlib.sha256(payload).hexdigest(),'stream binding')
        require(all((ROOT/p['path']).stat().st_size<=97 for p in index['parts']),'part size bound')
        with PartWriter('compressed',Path(directory),limit=97) as compressed:
            with gzip.GzipFile(fileobj=compressed,mode='wb',mtime=0) as zipped:
                with tarfile.open(fileobj=zipped,mode='w|') as archive:
                    info=tarfile.TarInfo('payload');info.size=len(payload)
                    archive.addfile(info,io.BytesIO(payload))
        with PartReader(compressed.index()['parts']) as parts,tarfile.open(fileobj=parts,mode='r|gz') as archive:
            member=archive.next()
            require(member.name=='payload' and archive.extractfile(member).read()==payload and archive.next() is None,
                    'compressed multipart stream replay')
    cells=roster();require(len(cells)==512 and len({c['id'] for c in cells})==512,'roster coverage')
    require(cells==roster() and cells!=roster(seed=400075),'seed determinism')
    for family,tier in {(c['family'],c['tier']) for c in cells}:
        require(sum(c['position']==0 for c in cells if c['family']==family and c['tier']==tier and c['lane']=='native')==16,
                'balanced pair order')
    require({c['id'] for c in cells}=={c['id'] for c in load(PRIOR/'confirmation-freeze.json')['cells']},'same planned scope')
    sessions=load(BASE/'resource-pilot-v1/result.json')['sessions']
    f=load(PRIOR/'confirmation-freeze.json')
    f.update(blocks=1,count=32,cells=[{k:s[k] for k in ('id','block','family','tier','lane','position')} for s in sessions])
    result=assess(f,sessions,DiskRecords(),[])
    require(result['status']=='complete-confirmation' and result['solves']==512,'pilot analysis coverage')
    failed=assess(f,sessions,DiskRecords(),[],[0])
    require(failed['status']=='incomplete-confirmation' and not any(r['useful_scoped_gain'] for r in failed['rows']),
            'resource refusal did not suppress decision')
    missing=assess(f,sessions[1:],DiskRecords(),[sessions[0]['id']])
    require(missing['status']=='incomplete-confirmation','missing session accepted')
    rejected=[]
    for name in ('duplicate','work','configuration','response-hash','original-authority','cost-partition'):
        changed=copy.deepcopy(sessions);records=DiskRecords()
        if name=='duplicate':changed.append(changed[0])
        elif name=='work':changed[0]['records'][0]['physical']+=1
        elif name=='configuration':changed[0]['tier']='invalid'
        elif name=='cost-partition':changed[0]['complete_session_ns']=0
        else:
            rr=changed[0]['records'][0];raw=records[rr['result']['path']]
            if name=='response-hash':raw+=b' '
            else:
                response=json.loads(raw);response['model_sha256']='0'*64
                raw=json.dumps(response).encode();rr['result']['sha256']=hashlib.sha256(raw).hexdigest()
            class Mutated:
                def __getitem__(self,key):
                    return raw if key==rr['result']['path'] else DiskRecords()[key]
            records=Mutated()
        try:assess(f,changed,records,[])
        except (RuntimeError,ValueError):rejected.append(name)
        else:raise RuntimeError('corruption accepted: '+name)
    put(BASE/'analysis-admission-v1.json',dict(status='passed',source=ref(__file__),analysis=ref(ROOT/'tools/lp_mixed2_reuse_analysis.py'),
        roster_cells=len(cells),pilot_sessions=len(sessions),pilot_responses=result['solves'],
        mutations_rejected=rejected,resource_and_missing_fail_closed=True,bounded_stream_roundtrip=True,scientific_result=False))
    print('prospective roster and six corruption guards passed',flush=True)


if __name__=='__main__':main()
