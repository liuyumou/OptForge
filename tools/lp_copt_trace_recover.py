"""Recover only checksum-proven QdstrmImporter telemetry append mutations."""
import argparse
import hashlib
from pathlib import Path
import struct
import time
from lp_protocol import checked_reference,file_hash,local,read_json,write_json


def varint(data,position):
    value=0
    for shift in range(0,70,7):
        if position>=len(data):raise ValueError('truncated stream index')
        byte=data[position];position+=1;value|=(byte&127)<<shift
        if not byte&128:return value,position
    raise ValueError('invalid stream index integer')


def fields(data):
    position=0;result=[]
    while position<len(data):
        first=position;tag,position=varint(data,position);wire=tag&7
        if wire==2:
            size,position=varint(data,position)
            if size>len(data)-position:raise ValueError('truncated stream index field')
            value=data[position:position+size];position+=size
        elif wire==0:value,position=varint(data,position)
        else:raise ValueError('unsupported stream index field')
        result.append((tag>>3,value,first,position))
    return result


def original_bytes(data,expected_sha256):
    """No candidate is accepted unless its entire historical SHA-256 matches."""
    if len(data)<16 or data[-8:]!=b'U3w[END]':raise ValueError('unknown stream footer')
    offset=struct.unpack('<Q',data[-16:-8])[0]
    if offset>=len(data)-16:raise ValueError('invalid stream index location')
    index=data[offset:-16]
    for _,entry,lo,hi in fields(index):
        if not isinstance(entry,bytes):raise ValueError('invalid stream section')
        values={key:value for key,value,*_ in fields(entry)}
        if values.get(1)!=b'Telemetry Status':continue
        start,size=values.get(2),values.get(3)
        if not isinstance(start,int) or not isinstance(size,int) or start+size!=offset:raise ValueError('telemetry is not the final appended section')
        candidate=data[:start]+index[:lo]+index[hi:]+struct.pack('<Q',start)+data[-8:]
        if hashlib.sha256(candidate).hexdigest()!=expected_sha256:raise ValueError('no exact historical checksum match; refuse recovery')
        return candidate
    raise ValueError('no appended telemetry section')


def restore(directory):
    rows=[];backup=directory/'offline-import-mutated';backup.mkdir(exist_ok=True)
    for path in sorted(directory.glob('*trace*.cost.json')):
        ref=read_json(path)['trace']
        if not ref:continue
        raw=local(directory,ref['path']);data=raw.read_bytes();before=file_hash(raw)
        if before==ref['sha256']:continue
        candidate=original_bytes(data,ref['sha256']);saved=backup/raw.name
        with saved.open('xb') as stream:stream.write(data)
        # The affected copy is preserved before restoring the proven original.
        temporary=raw.with_suffix('.recovering')
        with temporary.open('xb') as stream:stream.write(candidate)
        temporary.replace(raw);checked_reference(directory,ref)
        rows.append(dict(path=raw.name,recorded_sha256=ref['sha256'],imported_sha256=before,imported_copy=str(saved.relative_to(directory)),
                         before_bytes=len(data),original_bytes=len(candidate),removed_bytes=len(data)-len(candidate)))
    receipt=directory/('trace-recovery-'+str(time.time_ns())+'.json')
    write_json(receipt,dict(gpu_work=False,method='remove appended Telemetry Status section and rebuild its index; require exact historical whole-file SHA-256',
        tool_sha256=file_hash(Path(__file__)),captures=rows))
    print(len(rows),'captures restored exactly; imported copies and receipt retained:',receipt)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);a=p.parse_args();restore(a.directory)
