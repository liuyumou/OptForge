"""A fresh tail must not repeat completed, failed, or interrupted scientific cells."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_copt_tail import unattempted
class CoptTailContracts(unittest.TestCase):
    def test_all_attempted_outcomes_are_excluded_without_reordering(self):
        cells=[{'id':x,'seconds':100} for x in ['passed','failed','new-a','missing','new-b']]
        tail=unattempted(cells,{'passed','failed','missing'})
        self.assertEqual([c['id'] for c in tail],['new-a','new-b']);tail[0]['seconds']=300;self.assertEqual(cells[2]['seconds'],100)
    def test_duplicate_identity_is_refused(self):
        with self.assertRaisesRegex(ValueError,'unique'):unattempted([{'id':'x'},{'id':'x'}],set())
if __name__=='__main__':unittest.main()
