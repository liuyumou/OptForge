"""Source-only device experiment contracts; no driver or toolkit execution."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
import lp_state_device as device
import lp_state_admission as admission
from lp_expansion_oracle import primitive_result, round_fraction, power2


class StateDeviceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=device.corpus()

    def endpoint(self,job):
        request=device.request_for(job,Path("/frozen"))
        endpoint=dict(schema_version=1,request=request,device=dict(uuid=device.DEVICE),
                      context_ns=1,module_stream_ns=1,allocation_ns=1,teardown_ns=1,process_work_ns=1,launches=[])
        expected={p:[c["expected"] for c in self.corpus["cases"] if c["precision"]==p] for p in (48,64)}
        for launch in device.launch_plan(job):
            p,n,k=launch["precision"],launch["count"],launch["iterations"]
            values=expected[p][:n] if k is None else [device.expected_benchmark(p,launch["pattern"],k,i%17) for i in range(n)]
            endpoint["launches"].append(dict(launch,values=copy.deepcopy(values+[device.SENTINEL]),
                cycles=([0] if k is None else [100])*n+[0],allocated_bytes=(3086 if job["mode"]=="check" else n+1)*76,
                kernel=f"state_compact_fma_p{p}" if k is None else f"state_bench_p{p}",
                host_prepare_ns=1,upload_ns=1,launch_sync_ns=1,download_ns=1))
        return request,endpoint

    def test_fixed_roster_fits_original_task_and_phase_caps(self):
        jobs=device.roster()
        self.assertEqual(len(jobs),42)
        self.assertEqual(len({j["id"] for j in jobs}),42)
        totals={c:sum(j["seconds"]+6 for j in jobs if j["category"]==c) for c in ("accept","timing")}
        self.assertEqual(totals,dict(accept=456,timing=576))
        self.assertEqual(sum(totals.values()),1032)
        malformed=device.protocol();malformed["combined_cap_seconds"]=1101
        with self.assertRaisesRegex(ValueError,"authority differs"):device.ledger_for(malformed)
        self.assertEqual([j["gate"] for j in jobs[:6]],
                         ["oracle","repeat","memcheck","racecheck","initcheck","synccheck"])

    def test_unsigned_wire_preserves_full_64_bit_values_and_overflow_sentinels(self):
        self.assertEqual(len(self.corpus["cases"]),6170)
        self.assertEqual([sum(c["precision"]==p for c in self.corpus["cases"]) for p in (48,64)],[3085,3085])
        self.assertTrue(any(v[0]>2**63 for c in self.corpus["cases"] for v in c["input"]))
        self.assertTrue(any(c["expected"]==device.SENTINEL[:3]+[2] for c in self.corpus["cases"]))

    def test_alternate_device_preserves_combined_authority(self):
        current=device.protocol()
        try:
            device.select_cohort("v1")
            previous=device.protocol()
        finally:
            device.select_cohort("v2")
        charge=current["prior_gpu_ns"]-previous["prior_gpu_ns"]
        self.assertEqual(charge,3002084480)
        self.assertNotEqual(current["device"],previous["device"])
        self.assertEqual(current["prior_events"],previous["prior_events"]+2)
        self.assertLessEqual(current["combined_cap_seconds"]*10**9+charge,
                             previous["combined_cap_seconds"]*10**9)
        self.assertLessEqual(current["categories"]["accept"]["seconds"]*10**9+charge,
                             previous["categories"]["accept"]["seconds"]*10**9)

    def test_benchmark_endpoints_match_stepwise_fraction_oracle(self):
        for p in (48,64):
            fmt=(p,-1022,1023);one=1<<(p-1)
            for pattern in device.PATTERNS:
                for residue in range(17):
                    x=round_fraction((one+residue)*power2(-(p-1)),fmt)
                    b=round_fraction(1 if pattern=="increment" else -1,fmt)
                    c=round_fraction(power2(-(p-1)) if pattern=="increment" else
                                     power2(-1022-(p-1)) if pattern=="far_tail" else 1,fmt)
                    for iterations in range(1,10):
                        x=primitive_result("fma",[x,b,c],fmt)
                        self.assertEqual(device.expected_benchmark(p,pattern,iterations,residue),admission.wire(x)+[0])

    def test_device_verifier_checks_all_launches_and_canaries(self):
        job=device.roster()[0];request,endpoint=self.endpoint(job)
        device.verify_endpoint(endpoint,job,request,self.corpus)
        for mutate in (
            lambda e:e["launches"].pop(),
            lambda e:e["launches"][0]["values"][0].__setitem__(0,0),
            lambda e:e["launches"][0]["values"][-1].__setitem__(3,0),
            lambda e:e["launches"][0].__setitem__("kernel","state_full_fma_p48"),
            lambda e:e["launches"][0].__setitem__("repeat",False),
            lambda e:e["device"].__setitem__("uuid","GPU-wrong"),
        ):
            broken=copy.deepcopy(endpoint);mutate(broken)
            with self.assertRaises(ValueError):device.verify_endpoint(broken,job,request,self.corpus)

    def test_timing_requires_both_warmup_and_measured_endpoints(self):
        job=device.roster()[6];request,endpoint=self.endpoint(job)
        device.verify_endpoint(endpoint,job,request,self.corpus)
        for key,value in (("launch_sync_ns",0),("allocated_bytes",False),("iterations",16384)):
            broken=copy.deepcopy(endpoint);broken["launches"][1][key]=value
            with self.assertRaises(ValueError):device.verify_endpoint(broken,job,request,self.corpus)
        endpoint["launches"][0]["values"][0][0]+=1
        with self.assertRaisesRegex(ValueError,"independent device FMA"):device.verify_endpoint(endpoint,job,request,self.corpus)

    def test_sanitizer_command_binding_and_freeze_inventory(self):
        root=Path("/frozen")
        for job in device.roster()[:6]:
            command=device.command_for(job,root,Path("request"),Path("endpoint"))
            self.assertEqual(command[-3:],["/frozen/lp_state_probe","request","endpoint"])
            if job["gate"] in ("oracle","repeat"):self.assertEqual(len(command),3)
            else:self.assertEqual(command[:5],["/usr/local/cuda/bin/compute-sanitizer","--error-exitcode","99","--tool",job["gate"]])
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary);(path/"freeze.json").write_text(json.dumps({"files":{}}))
            with self.assertRaisesRegex(ValueError,"inventory differs"):device.verify_freeze(path)

    def test_sanitizer_summary_accepts_either_captured_stream(self):
        clean="========= COMPUTE-SANITIZER\n========= ERROR SUMMARY: 0 errors\n"
        self.assertTrue(device.sanitizer_ok(clean,""))
        self.assertTrue(device.sanitizer_ok("",clean))
        self.assertFalse(device.sanitizer_ok("",clean.replace("0 errors","1 errors")))
        self.assertFalse(device.sanitizer_ok("ERROR SUMMARY: 0 errors truncated",""))
        self.assertFalse(device.sanitizer_ok("state primitive endpoint complete",""))
        self.assertFalse(any(p.startswith("crates/") or p.endswith(".cu") or
                             p.endswith("lp_supervise.py") for p in device.REPAIR_FILES))

    def test_torn_or_wrong_ledger_refuses_before_reporting_costs(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/"ledger.jsonl"
            path.write_text('{"not":"an event"}')
            with self.assertRaisesRegex(ValueError,"torn"):device.verify_budget(path,{})
            path.write_text('{}\n')
            with self.assertRaisesRegex(ValueError,"prefix differs"):device.verify_budget(path,{})


if __name__=="__main__":unittest.main()
