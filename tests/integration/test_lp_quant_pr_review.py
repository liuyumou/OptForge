"""Portable checks of the CPU-only PR bridge, with no ignored study artifacts."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_protocol import ROOT,read_json,file_hash
import lp_quant_pr_review as review
import lp_quant_report_output as output


class QuantPrReview(unittest.TestCase):
    def test_current_source_matches_explicit_review_scope(self):
        receipt=read_json(review.RECEIPT)
        self.assertEqual(receipt['base_commit'],review.BASE)
        self.assertEqual(receipt['gpu_seconds'],0)
        self.assertFalse(receipt['new_device_acceptance'])
        self.assertEqual({f['path'] for f in receipt['files']},review.CHANGED)
        self.assertEqual({f['path'] for f in receipt['added']},review.ADDED)
        for f in receipt['files']:
            self.assertEqual(file_hash(ROOT/f['path']),f['reviewed_sha256'])
        # Later accepted slices extend module/example/acceptance registration.
        # Verify the original receipt against immutable original bytes, then bind
        # each authorized live extension through its separate follow-up receipt.
        for f in receipt['added']+receipt['unchanged_sources']:
            current=file_hash(ROOT/f['path'])
            if current==f['sha256']:continue
            previous=f['sha256']
            for cohort in ['tensor','tensor-residual','tensor-cost','tensor-warp32','baseline-pr']:
                path=ROOT/('docs/benchmarks/data/'+cohort+'/prerequisite-source-bridge.json')
                if not path.exists():continue
                rows={row['path']:row for row in read_json(path)['files']}
                if f['path'] not in rows:continue
                extension=rows[f['path']]
                self.assertEqual(extension['before_sha256'],previous)
                self.assertEqual(file_hash(ROOT/extension['frozen_path']),previous)
                previous=extension['after_sha256']
            self.assertEqual(current,previous)

    def test_arithmetic_controller_and_authority_bodies_remain_exact(self):
        import hashlib
        for f in read_json(review.RECEIPT)['unchanged_bodies']:
            body=review.section((ROOT/f['path']).read_bytes(),f['start'],f['end'])
            self.assertEqual(hashlib.sha256(body).hexdigest(),f['sha256'])

    def test_output_alias_and_existing_file_rejections_are_portable(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);history=root/'historical.json';history.write_text('unchanged')
            reports=root/'review';reports.mkdir()
            with patch.object(output,'DIRECTORY',reports):
                self.assertEqual(output.report_output(),reports/'resident-report.json')
                for kind in ['symlink','hardlink','existing']:
                    p=reports/(kind+'.json')
                    if kind=='symlink':p.symlink_to(history)
                    elif kind=='hardlink':os.link(history,p)
                    else:p.write_text('previous attempt')
                    with self.assertRaises(ValueError):output.report_output(p)
                with self.assertRaises(ValueError):output.report_output(history)
                with self.assertRaises(ValueError):output.report_output(reports/'..'/'historical.json')
            self.assertEqual(history.read_text(),'unchanged')

    def test_execution_admission_requires_current_numerical_source_receipt(self):
        from lp_quant_resident_budget import protocol
        # Reviewing a boundary is not fresh device admission for the rebuilt
        # executable. Preserve the original admission rather than retcon it.
        with self.assertRaisesRegex(ValueError,'exact CPU admission required'):
            protocol()


if __name__=='__main__':unittest.main()
