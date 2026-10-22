"""Refinement review: fail-closed generated-instruction inspection."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import hashlib

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from lp_refine_admission import instruction_counts
import lp_refine_review as review


class RefineInstructionReview(unittest.TestCase):
    def test_normal_and_uniform_predicates_are_fully_parsed(self):
        for predicate in ['', '@P0 ', '@!P1 ', '@UP2 ', '@!UPT ', '@PT ']:
            self.assertEqual(instruction_counts(' /*0010*/ '+predicate+'FMUL R0, R1, R2;'),{'FMUL':1})

    def test_unknown_predicates_and_incomplete_instructions_refuse(self):
        for line in [' /*0010*/ @BAD FMUL R0, R1, R2;', ' /*0010*/ @UP2 ;',
                     ' /*0010*/ R3;', ' /*0010*/ FMUL R0, R1, R2', '']:
            with self.subTest(line=line),self.assertRaises(ValueError):instruction_counts(line)

    def test_atomics_reductions_and_unaudited_calls_refuse(self):
        for op in ['ATOM.E.ADD','RED.E.ADD','CALL.ABS.NOINC','JCAL']:
            for predicate in ['', '@!UPT ']:
                with self.subTest(op=op,predicate=predicate),self.assertRaises(ValueError):
                    instruction_counts(' /*AB10*/ '+predicate+op+' R0, R1;')


class RefineSourceReview(unittest.TestCase):
    def receipt(self):
        return dict(identity='gpup-refine-review-source-v1',base_revision=review.BASE,
                    files=[dict(path='tools/report_lp_refine.py',before_sha256=hashlib.sha256(b'old').hexdigest(),reviewed_sha256='b'*64)])

    def test_scope_and_duplicate_changes_refuse_before_git_access(self):
        for path in ['cuda/lp_pdhg_refine/lp_pdhg_refine.cu','../outside']:
            value=self.receipt();value['files'][0]['path']=path
            with patch.object(review.subprocess,'run') as git,self.assertRaises(ValueError):
                review.validate_receipt(value)
            git.assert_not_called()
        value=self.receipt();value['files']*=2
        with patch.object(review.subprocess,'run') as git,self.assertRaises(ValueError):review.validate_receipt(value)
        git.assert_not_called()

    def test_both_base_and_reviewed_hashes_are_required(self):
        value=self.receipt()
        with patch.object(review.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'wrong')),self.assertRaises(ValueError):review.validate_receipt(value)
        with patch.object(review.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'old')),patch.object(review,'sha',return_value='c'*64),self.assertRaises(ValueError):review.validate_receipt(value)
        with patch.object(review.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'old')),patch.object(review,'sha',return_value='b'*64):
            self.assertEqual(set(review.validate_receipt(value)),{'tools/report_lp_refine.py'})

    def test_cached_receipt_does_not_mask_later_source_mutation(self):
        with patch.object(review,'changes',return_value={'tools/report_lp_refine.py':self.receipt()['files'][0]}),patch.object(review,'sha',return_value='c'*64),self.assertRaises(ValueError):
            review.pre_review_sha('tools/report_lp_refine.py')


if __name__=='__main__':unittest.main()
