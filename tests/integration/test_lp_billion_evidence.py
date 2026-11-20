"""The portable integrity replay must use retained bytes and reject mutation."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_portable import replay,evidence_files
from lp_billion_campaign import endpoint_bytes
import lp_billion_campaign as campaign
import lp_billion_common as common
import lp_billion_budget as budget


class BillionEvidenceContracts(unittest.TestCase):
    def test_cpu_fallback_has_no_cuda_instrumentation_but_gpu_errors_stay_fatal(self):
        from lp_billion_prepare_admit import instrument
        command=['executor','prepare-check','long-line']
        self.assertEqual(instrument(command,'memcheck','log',True),command)
        gpu=instrument(command,'memcheck','log',False)
        self.assertEqual(gpu[-3:],command)
        self.assertEqual(gpu[gpu.index('--error-exitcode')+1],'99')
        self.assertIn('compute-sanitizer',gpu[0])
        race=instrument(command,'racecheck','log')
        self.assertEqual(race[race.index('--force-synchronization-limit')+1],'8')
        self.assertEqual(race[race.index('--racecheck-num-workers')+1],'3')
        self.assertNotIn('--launch-count',race)
        self.assertNotIn('--kernel-name',race)
        self.assertNotIn('--kernel-name-exclude',race)

    def test_dependency_locks_are_evidence_while_live_root_locks_are_not(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            names=['budget.lock','cpu.lock','sources/job/Cargo.lock',
                   'sources/job/research/Cargo.lock','dependencies/hash/Cargo.lock']
            for name in names:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('retained')
            found={str(p.relative_to(root)) for p in evidence_files(root,[])}
            self.assertEqual(found,set(names[2:]))

    def test_new_checkpoint_keeps_previous_catalogs_and_excludes_only_current_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            names=['portable/old/manifest.json','portable/current/manifest.json',
                   'portable-view/data','target/cache','resources/live.request.json',
                   'resources/old.settlement.json','objects/data.bin']
            for name in names:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
            found={str(p.relative_to(root)) for p in evidence_files(root,['live'],root/'portable/current')}
            self.assertEqual(found,{'portable/old/manifest.json','resources/old.settlement.json','objects/data.bin'})

    def test_borrowed_capacity_removes_only_operator_array_allowance(self):
        model=dict(rows=62500000,columns=62500000,nonzeros=1000000000,canonical_tiles=0,covered_nnz=0)
        for lane in ['native','fp32','fp4x2']:
            before=campaign.capacity(model,lane);after=campaign.capacity(model,lane,True)
            self.assertEqual(before['host_bytes']-after['host_bytes'],24*(1<<30))
            self.assertEqual(before['device_bytes'],after['device_bytes'])
            self.assertEqual(before['endpoint_bytes_upper'],after['endpoint_bytes_upper'])
            self.assertEqual((before['formula_version'],after['formula_version']),(2,3))

    def test_preparation_partitions_do_not_mask_numerical_changes(self):
        from lp_billion_admit import canonical as admission
        from lp_billion_results import canonical as campaign_canonical
        old=dict(logical=100,certified=False,cost_ns=dict(host_preparation=10))
        new=dict(old,preparation_detail_ns=dict(engine=3,operator=1,packing=4,control_initialization=2))
        for canonical in [admission,campaign_canonical]:
            self.assertEqual(canonical(old),canonical(new))
            self.assertNotEqual(canonical(old),canonical(dict(new,logical=101)))

    def test_storage_reserves_a_repaired_dual_at_every_assessment(self):
        self.assertEqual(endpoint_bytes(dict(rows=11,columns=7),500),3*8*(7+22))
        self.assertEqual(endpoint_bytes(dict(rows=11,columns=7),501),4*8*(7+22))

    def test_freeze_binds_all_lanes_and_complete_endpoint_allowance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with mock.patch.object(common,'BASE',root), mock.patch.object(campaign,'BASE',root), mock.patch.object(budget,'BASE',root):
                common.put(root/'resources/array-memcheck-v3.settlement.json',
                           dict(status='refused',cleanup_empty=True,overrun=False))
                common.put(root/'resources/array-racecheck-v3.settlement.json',
                           dict(status='refused',cleanup_empty=True,overrun=False))
                common.put(root/'resources/array-racecheck-v4.settlement.json',
                           dict(status='refused',cleanup_empty=True,overrun=False))
                common.put(root/'resources/array-racecheck-v5.settlement.json',
                           dict(status='refused',cleanup_empty=True,overrun=False))
                common.put(root/'resources/idle-confirmation-v5.settlement.json',
                           dict(status='refused',cleanup_empty=True,overrun=False))
                common.put(root/'resources/operational-cpu-v9.settlement.json',dict(status='passed'))
                common.put(root/'resources/preparation-harness-cpu-v6.settlement.json',dict(status='passed'))
                for name in ['billion-native-v2','array-gpu-v3','array-memcheck-v4',
                             'array-racecheck-v6','array-initcheck-v3','array-synccheck-v3',
                             'generator-admission-v1','ownership-audit-v2']:
                    common.put(root/'resources'/(name+'.settlement.json'),dict(status='passed'))
                original=root/'input/model.json';common.put(original,{})
                common.put(original.with_name('construction-check.json'),dict(accepted=True,model=common.ref(original)))
                model=original.with_name('result.json')
                common.put(model,dict(status='generated',model=common.ref(original),family='irregular',
                    rows=11,columns=7,nonzeros=22,canonical_tiles=0,covered_nnz=0))
                common.put(root/'image-v3/binding.json',{})
                manifest=campaign.freeze('cohort',[model],['native','fp32','fp4x2'],501,1000,10,version=3)
                cells=common.load(manifest)['cells']
                self.assertEqual([c['lane'] for c in cells],['native','fp32','fp4x2'])
                self.assertEqual([c['id'] for c in cells],['cohort-0-native','cohort-0-fp32','cohort-0-fp4x2'])
                self.assertTrue(all(c['status']=='pending' for c in cells))
                self.assertTrue(all(c['memory']['endpoint_bytes_upper']==4*8*(7+22) for c in cells))
                self.assertTrue(all(c['request']['fast']['gpu_preparation'] for c in cells))
                proof_paths={p['path'] for p in common.load(manifest)['admission']}
                self.assertIn('resources/array-memcheck-v3.settlement.json',proof_paths)
                self.assertIn('resources/array-memcheck-v4.settlement.json',proof_paths)

    def fixture(self,root):
        payload=b'\x00'*8;sha=hashlib.sha256(payload).hexdigest()
        (root/'objects').mkdir();(root/'objects'/f'{sha}.bin').write_bytes(payload)
        doc=dict(endpoint=dict(primal=dict(dtype='f64le',count=1,chunks=[dict(bytes=8,sha256=sha)])),
                 source=dict(namespace='repo',path='unavailable/source.rs',bytes=8,sha256=sha))
        (root/'record.json').write_text(json.dumps(doc))
        entries=[dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                 for p in [root/'objects'/f'{sha}.bin',root/'record.json']]
        manifest=root/'manifest.json';manifest.write_text(json.dumps(dict(entries=entries,
            external=[dict(original=doc['source'],portable_path=f'objects/{sha}.bin')])) )
        return manifest,root/'objects'/f'{sha}.bin'

    def test_replay_uses_portable_source_without_original_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);manifest,_=self.fixture(root)
            replay(root,manifest,root/'result.json')
            result=json.loads((root/'result.json').read_text())
            self.assertEqual(result['status'],'passed')
            self.assertEqual(result['array_references'],1)
            self.assertFalse(result['original_repository_access_required'])

    def test_replay_rejects_mutated_endpoint_chunk(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);manifest,chunk=self.fixture(root);chunk.write_bytes(b'\x01'*8)
            with self.assertRaisesRegex(ValueError,'portable bytes'):
                replay(root,manifest,root/'result.json')


if __name__=='__main__':
    unittest.main()
