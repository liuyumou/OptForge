"""Differential admission for a new compiled schema path; no solver calls."""
import copy
import json
from pathlib import Path
import random
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from lp_baseline_fast import validator
from validate_artifacts import validator as original


class CompiledSchemas(unittest.TestCase):
    def test_schema_equivalence_and_no_mutation(self):
        rng=random.Random(17112)
        for schema,example in [('lp-baseline-model-v1.schema.json','lp-baseline-model-v1.json'),
                               ('lp-baseline-endpoint-v1.schema.json','lp-baseline-endpoint-v1.synthetic.json')]:
            base=json.loads((ROOT/'examples'/example).read_text())
            variants=[base,dict(base,unexpected=True)]
            for key in base:
                d=copy.deepcopy(base);d.pop(key);variants.append(d)
                for invalid in [True,{},'bad',None]:
                    d=copy.deepcopy(base);d[key]=invalid;variants.append(d)
            for _ in range(64):
                d=copy.deepcopy(base)
                key=rng.choice(['variable_ids','row_ids'])
                d[key]=rng.choice([[True],[1.5],[-1],[2**32],[0,0],[],[0],[1.,2.]])
                variants.append(d)
            for value in variants:
                before=json.dumps(value,sort_keys=True)
                outcomes=[]
                for reader in [original(schema),validator(schema)]:
                    try: reader.validate(value);outcomes.append(True)
                    except Exception: outcomes.append(False)
                self.assertEqual(outcomes[0],outcomes[1],(schema,value))
                self.assertEqual(json.dumps(value,sort_keys=True),before)

    def test_numeric_authority_source_is_unchanged(self):
        old=(ROOT/'research/lp-external-baseline/src/main.rs').read_text()
        new=(ROOT/'research/lp-external-baseline-buffered/src/main.rs').read_text()
        body=lambda s:s.split('fn assess(',1)[1].split('\nfn write(',1)[0]
        self.assertEqual(body(old),body(new))
        self.assertEqual((ROOT/'research/lp-external-baseline/src/strict.rs').read_bytes(),
                         (ROOT/'research/lp-external-baseline-buffered/src/strict.rs').read_bytes())


if __name__=='__main__': unittest.main()
