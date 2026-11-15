"""Portable archive corruption and path checks; all fixtures are synthetic."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import replay_gpup9_archive as archive


class Gpup9ArchiveTests(unittest.TestCase):
    def make(self,root,corrupt_entry=False,duplicate=False):
        directory=root/'docs/benchmarks/data';directory.mkdir(parents=True)
        name='artifacts/gpup9-v1/design-v2.json';body=b'{"source":[]}'
        metadata=dict(schema_version=1,kind='gpup9-portable-evidence',files=[name],
            entries={name:dict(bytes=len(body),sha256=('0'*64 if corrupt_entry else hashlib.sha256(body).hexdigest()))})
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as z:
            z.writestr('manifest.json',json.dumps(metadata));z.writestr(name,body)
            if duplicate:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore',UserWarning);z.writestr(name,body)
        raw=buffer.getvalue();part=directory/'fixture.part00';part.write_bytes(raw)
        index=dict(schema_version=1,kind='gpup9-split-zip-v1',parts=[dict(path=str(part.relative_to(root)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())],
                   bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),files=1,pending_administration=[])
        path=directory/'fixture.json';path.write_text(json.dumps(index))
        return path,index,part

    def test_minimal_archive_replays_without_artifacts_directory(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path,index,part=self.make(root)
            with patch.object(archive,'ROOT',root):result=archive.replay(path)
            self.assertEqual(result['status'],'passed')
            self.assertEqual(result['exact_files'],1)
            self.assertFalse((root/'artifacts').exists())

    def test_changed_part_and_rehashed_corrupt_entry_are_rejected(self):
        for corrupt_entry in [False,True]:
            with self.subTest(corrupt_entry=corrupt_entry),tempfile.TemporaryDirectory() as d:
                root=Path(d);path,index,part=self.make(root,corrupt_entry)
                if not corrupt_entry:part.write_bytes(part.read_bytes()+b'changed')
                with patch.object(archive,'ROOT',root),self.assertRaises(Exception):archive.replay(path)

    def test_escape_duplicate_and_boolean_size_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path,index,part=self.make(root)
            for mutation in ['escape','duplicate','boolean']:
                changed=json.loads(json.dumps(index))
                if mutation=='escape':changed['parts'][0]['path']='../outside.part'
                elif mutation=='duplicate':changed['parts']*=2
                else:changed['parts'][0]['bytes']=True
                with self.subTest(mutation=mutation),self.assertRaises(Exception):archive.verify_index(changed,root)

    def test_duplicate_zip_members_refuse_even_when_bytes_match(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path,index,part=self.make(root,duplicate=True)
            with patch.object(archive,'ROOT',root),self.assertRaises(Exception):archive.replay(path)



    def test_zip_streams_and_seeks_across_bounded_parts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);directory=root/'docs/benchmarks/data';directory.mkdir(parents=True)
            content=bytes(range(256))*5;index_path=directory/'stream.json'
            with patch.object(archive,'ROOT',root):
                sink=archive.PartWriter(index_path,chunk=97)
                with zipfile.ZipFile(sink,'w',compression=zipfile.ZIP_DEFLATED,allowZip64=True) as z:
                    with z.open('payload','w',force_zip64=True) as dest:dest.write(content)
                index=sink.finish()
            self.assertGreater(len(index['parts']),3)
            self.assertTrue(all((root/p['path']).stat().st_size<=97 for p in index['parts']))
            original=b''.join((root/p['path']).read_bytes() for p in index['parts'])
            with archive.PartReader(index,root) as source:
                source.seek(96);self.assertEqual(source.read(99),original[96:195])
                source.seek(-11,2);self.assertEqual(source.read(),original[-11:])
                source.seek(0)
                with zipfile.ZipFile(source) as z:self.assertEqual(z.read('payload'),content)
                with self.assertRaises(ValueError):source.seek(-1)


    @unittest.skipUnless(importlib.util.find_spec("zstandard"), "install optional GPUP-9 evidence requirements")
    def test_solid_compression_replays_and_rejects_expansion_mismatch(self):
        import zstandard
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path,index,part=self.make(root)
            original=part.read_bytes()
            encoded=io.BytesIO()
            parameters=zstandard.ZstdCompressionParameters.from_level(6,window_log=25,threads=0)
            with zstandard.ZstdCompressor(compression_params=parameters).stream_writer(encoded,closefd=False) as output:
                counter=archive.CountingWriter(output)
                with zipfile.ZipFile(io.BytesIO(original)) as old,zipfile.ZipFile(counter,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as new:
                    for item in old.infolist():new.writestr(item.filename,old.read(item))
                expanded_size=counter.tell()
            compressed=encoded.getvalue()
            part.write_bytes(compressed)
            index.update(kind='gpup9-split-zstd-zip-v1',zip_bytes=expanded_size,bytes=len(compressed),sha256=hashlib.sha256(compressed).hexdigest())
            index['parts'][0].update(bytes=len(compressed),sha256=index['sha256'])
            path.write_text(json.dumps(index))
            with patch.object(archive,'ROOT',root):self.assertEqual(archive.replay(path)['status'],'passed')
            for delta in [-1,1]:
                index['zip_bytes']=expanded_size+delta;path.write_text(json.dumps(index))
                with patch.object(archive,'ROOT',root),self.assertRaises(Exception):archive.replay(path)
            index['zip_bytes']=True
            with self.assertRaises(Exception):archive.verify_index(index,root)

    def test_omitted_models_require_retained_generator_design_and_manifest_hashes(self):
        name='artifacts/gpup9-v1/models-v2/holdout/manifest.json'
        model='artifacts/gpup9-v1/models-v2/holdout/sample.json'
        design='artifacts/gpup9-v1/design-v2.json'
        value=dict(generator=dict(sha256='a'*64),design=dict(path=design,sha256='b'*64),
            groups={'sample':dict(models=[dict(path=model,sha256='c'*64)])})
        metadata=dict(entries={name:dict(sha256='d'*64),design:dict(sha256='b'*64),'source.py':dict(sha256='a'*64)},
            reproducible_models={model:dict(sha256='c'*64,bytes=100)})
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as z:z.writestr(name,json.dumps(value))
        with zipfile.ZipFile(buffer) as z:
            self.assertEqual(archive.model_bindings(metadata,z),{model:'c'*64})
            for mutation in ['model','source','design','escape','duplicate']:
                changed=json.loads(json.dumps(metadata))
                if mutation=='model':changed['reproducible_models'][model]['sha256']='f'*64
                elif mutation=='source':del changed['entries']['source.py']
                elif mutation=='design':changed['entries'][design]['sha256']='f'*64
                elif mutation=='escape':changed['reproducible_models']['../outside.json']=changed['reproducible_models'].pop(model)
                else:changed['entries'][model]=changed['reproducible_models'][model]
                with self.subTest(mutation=mutation),self.assertRaises(Exception):archive.model_bindings(changed,z)

    def closure_fixture(self,root):
        index,_,_=self.make(root);raw={}
        def entry(name,value):
            path='artifacts/gpup9-v1/'+name;body=json.dumps(value,sort_keys=True)
            raw[path]=body;return dict(path=path,sha256=hashlib.sha256(body.encode()).hexdigest())
        resource=entry('resources/failure.resource.json',dict(status='refused',guardian_cleanup=dict(empty=True),result=dict(cleanup=dict(empty=True))))
        reservation=entry('resources/failure.reservation.json',dict(phase='acceptance',gpu=True,cpu_ns=12*10**9,gpu_ns=3*10**9))
        settlement=entry('resources/failure.settlement.json',dict(phase='acceptance',gpu=True,cpu_ns=12*10**9,gpu_ns=3*10**9,status='refused',overrun=False,resource=resource))
        receipt=dict(reservation=reservation,settlement=settlement,resource=resource)
        cpu={k:0 for k in archive.CPU_CAPS};gpu={k:0 for k in archive.GPU_CAPS}
        cpu.update(implementation=512*10**9,cleanup=128*10**9,acceptance=12*10**9);gpu['acceptance']=3*10**9
        evidence=entry('evidence.json',dict(status='passed'))
        entry('published-files.json',dict(entries={}))
        closed=dict(status='closed',scientific_status='complete',cleanup_empty=True,public_defaults_changed=False,prep3_opened=False,publication=False,
            administration_cpu_seconds=dict(preparation=512,closing=128),resources=[receipt],failed=[receipt],cpu_phases_ns=cpu,gpu_phases_ns=gpu,
            cpu_ns=sum(cpu.values()),gpu_ns=sum(gpu.values()),cpu_ceiling_seconds=sum(archive.CPU_CAPS.values()),gpu_ceiling_seconds=sum(archive.GPU_CAPS.values()),
            historical=evidence,portable=evidence,analysis=evidence)
        entry('CLOSED.json',closed)
        with patch.object(archive,'ROOT',root):
            # ref() owns its imported module's root, so use the canonical path
            # returned by that function rather than guessing a relative prefix.
            binding=archive.ref(index)
        return index,dict(schema_version=1,kind='gpup9-closure',archive=binding,raw=raw,closed=closed,late_source_bytes={})

    def test_closure_recomputes_full_failed_reservation_and_rejects_changes(self):
        with tempfile.TemporaryDirectory(dir=archive.ROOT) as d:
            root=Path(d);index,value=self.closure_fixture(root)
            self.assertEqual(archive.verify_closure(value,index)['failed'],1)
            for mutation in ['receipt','total','missing','source','undercharged']:
                changed=json.loads(json.dumps(value))
                if mutation=='receipt':changed['raw']['artifacts/gpup9-v1/resources/failure.settlement.json']+=' '
                elif mutation=='total':changed['closed']['cpu_ns']-=1
                elif mutation=='missing':changed['closed']['resources']=[]
                elif mutation=='source':changed['late_source_bytes']['0'*64]='changed'
                else:
                    key='artifacts/gpup9-v1/resources/failure.settlement.json'
                    settlement=json.loads(changed['raw'][key]);settlement['cpu_ns']-=1
                    body=json.dumps(settlement,sort_keys=True);changed['raw'][key]=body
                    for field in ['resources','failed']:changed['closed'][field][0]['settlement']['sha256']=hashlib.sha256(body.encode()).hexdigest()
                    changed['closed']['cpu_ns']-=1;changed['closed']['cpu_phases_ns']['acceptance']-=1
                    changed['raw']['artifacts/gpup9-v1/CLOSED.json']=json.dumps(changed['closed'],sort_keys=True)
                with self.subTest(mutation=mutation),self.assertRaises(Exception):archive.verify_closure(changed,index)


    def test_rejected_fp4_attempts_do_not_count_as_accepted_work(self):
        response=dict(events=[dict(kind='window',lane=34,logical=16,step=dict(done=16)),
            dict(kind='recovery',logical=0),dict(kind='window',lane=32,logical=20,step=dict(done=20))],
            attempted={'34':16,'32':20},physical=36,logical=20)
        self.assertEqual(archive.accepted_work(response),{'32':20,'34':0,'36':0})
        response['events'][1]['logical']=8;response['events'][2]['logical']=28;response['logical']=28
        self.assertEqual(archive.accepted_work(response),{'32':20,'34':8,'36':0})

    def test_invalid_logical_transcript_refuses(self):
        response=dict(events=[dict(kind='window',lane=34,logical=17,step=dict(done=16))],
                      attempted={'34':16},physical=16,logical=16)
        with self.assertRaises(Exception):archive.accepted_work(response)


if __name__=='__main__':unittest.main()
