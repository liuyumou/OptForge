"""Compact original input refuses malformed data before native allocation."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_general_scale_io import read,write,from_document,memory_estimate
from lp_general_models import generate
from lp_general_scale_evidence import save as save_response,read as read_response
from lp_general_common import ROOT
from lp_general_scale_portable import verify_streams
import numpy as np

class ScaleInputTests(unittest.TestCase):
    def test_sparse_transport_preserves_original_bits_and_ids(self):
        doc,_=generate('irregular',33,91)
        doc['constraints'][0]['terms'][0]['coefficient']=-0.
        original=from_document(doc)
        with tempfile.TemporaryDirectory() as d:
            result=write(Path(d)/'m.lpcsr',original)
            for key in ['lower','upper','row_lower','row_upper','values','objective_values']:
                self.assertTrue(np.array_equal(result[key].view('u8'),np.asarray(original[key],dtype='f8').view('u8')),key)
            self.assertEqual(result['model_id'],doc['model_id'])
            self.assertEqual(result['column_ids'].tolist(),[v['id'] for v in doc['variables']])

    def test_compact_rejects_truncation_trailing_dimensions_and_nan(self):
        doc,_=generate('irregular',8,92)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'good';write(p,from_document(doc));b=p.read_bytes()
            bad=[b[:k] for k in [0,7,63,100,len(b)-1]]+[b+b'0']
            for at,value in [(8,(1<<20)+1),(24,(1<<26)+1),(32,2),(48,0),(56,9)]:
                c=bytearray(b);struct.pack_into('<Q',c,at,value);bad.append(bytes(c))
            c=bytearray(b);struct.pack_into('<d',c,len(c)-8,float('nan'));bad.append(bytes(c))
            for i,data in enumerate(bad):
                q=Path(d)/str(i);q.write_bytes(data)
                with self.assertRaises((ValueError,UnicodeDecodeError)):read(q)

    def test_compact_rejects_duplicate_columns_and_reversed_bounds(self):
        for kind in ['duplicate','bounds']:
            doc,_=generate('irregular',8,93);data=from_document(doc)
            if kind=='duplicate':data['indices'][1]=data['indices'][0]
            else:data['lower'][0]=2.;data['upper'][0]=1.
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(ValueError):write(Path(d)/'m',data)

    def test_memory_inventory_keeps_domain_and_full_representation(self):
        p=memory_estimate(2000000,1000000,1000000)
        self.assertFalse(p['admits_domain'])
        self.assertGreater(p['device_allowance_bytes'],p['compact_bytes'])
        self.assertGreater(memory_estimate(1000000,1000000,64000000)['host_allowance_bytes'],10<<30)

    def test_chunked_responses_roundtrip_and_reject_corruption(self):
        # Use small chunks to exercise boundaries without creating giant fixtures.
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as d:
            p=Path(d)/'response.json';original={'primal':[1.,-0.,1e-300]*31,'name':'λ'}
            text=json.dumps(original,ensure_ascii=False)+'\n'
            save_response(p,text,threshold=1,chunk_bytes=83)
            self.assertEqual(read_response(p),original)
            manifest=json.loads(p.read_text())
            self.assertGreater(len(manifest['parts']),1)
            part=ROOT/manifest['parts'][0]['path'];data=part.read_bytes()
            part.write_bytes(data[:-1])
            with self.assertRaises((AssertionError,RuntimeError,ValueError)):read_response(p)
            part.write_bytes(data)
            manifest['raw_bytes']+=1;p.write_text(json.dumps(manifest))
            with self.assertRaises((AssertionError,RuntimeError,ValueError)):read_response(p)

    def test_large_audit_stream_preserves_jsonl_bytes(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as d:
            p=Path(d)/'audit.jsonl';text='{"bound_proof":[1,2],"accepted":false}\n{"bound_proof":[1,2],"accepted":true}\n'
            save_response(p,text,threshold=1,chunk_bytes=17)
            result=verify_streams([p])
            self.assertEqual(result,dict(streams=1,raw_bytes=len(text.encode()),partial=[]))

if __name__=='__main__':unittest.main()
