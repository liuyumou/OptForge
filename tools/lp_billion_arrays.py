"""Portable immutable original-array and endpoint chunks (matching the Rust reader)."""
import hashlib
from pathlib import Path
import numpy as np
from lp_billion_common import require

CHUNK = 32 << 20
DTYPES = {'u32le':np.dtype('<u4'), 'u64le':np.dtype('<u8'), 'f64le':np.dtype('<f8')}

class Writer:
    def __init__(self, root, dtype):
        self.root = Path(root)
        (self.root/'objects').mkdir(parents=True, exist_ok=True)
        self.dtype, self.count, self.chunks, self.buffer = dtype, 0, [], bytearray()
    def add(self, values):
        values = np.asarray(values, dtype=DTYPES[self.dtype]).ravel()
        self.count += values.size
        data = memoryview(values).cast('B')
        while data:
            n = min(CHUNK-len(self.buffer), len(data))
            self.buffer.extend(data[:n]); data = data[n:]
            if len(self.buffer) == CHUNK:
                self.flush()
    def flush(self):
        if not self.buffer:return
        digest = hashlib.sha256(self.buffer).hexdigest()
        path = self.root/'objects'/(digest+'.bin')
        if path.exists():
            require(path.stat().st_size == len(self.buffer) and hashlib.sha256(path.read_bytes()).hexdigest()==digest, 'existing chunk differs')
        else:
            with path.open('xb') as f:f.write(self.buffer)
        self.chunks.append(dict(sha256=digest, bytes=len(self.buffer)))
        self.buffer.clear()
    def finish(self):
        self.flush()
        return dict(dtype=self.dtype, count=int(self.count), chunks=self.chunks)

def write(root, values, dtype='f64le'):
    w=Writer(root,dtype);w.add(values);return w.finish()

def read(root, array):
    require(array['dtype'] in DTYPES, 'array dtype')
    parts=[]
    for c in array['chunks']:
        require(len(c['sha256'])==64 and all(v in '0123456789abcdef' for v in c['sha256']) and 0<c['bytes']<=CHUNK,'chunk domain')
        path=Path(root)/'objects'/(c['sha256']+'.bin')
        require(path.resolve().is_relative_to(Path(root).resolve()),'chunk root escape')
        b=path.read_bytes()
        require(len(b)==c['bytes'] and hashlib.sha256(b).hexdigest()==c['sha256'],'chunk digest/length')
        parts.append(np.frombuffer(b,dtype=DTYPES[array['dtype']]))
    result=np.concatenate(parts) if parts else np.empty(0,dtype=DTYPES[array['dtype']])
    require(len(result)==array['count'],'array count')
    return result
