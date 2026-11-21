"""Source compaction preserves exact bytes and rejects corrupt retained objects."""
import hashlib,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_source_store import retain_source
class SourceStoreContracts(unittest.TestCase):
    def test_identical_versions_reuse_one_immutable_object(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);a=root/'a.rs';b=root/'b.rs';a.write_bytes(b'old');b.write_bytes(b'old')
            x=retain_source(a,root/'store');y=retain_source(b,root/'store')
            self.assertEqual(x,y);self.assertEqual(x.read_bytes(),b'old')
            self.assertEqual(len(list((root/'store').iterdir())),1)
            self.assertEqual(x.stat().st_mode & 0o222,0)
    def test_changed_source_retains_both_versions(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);p=root/'a.py';p.write_bytes(b'old');old=retain_source(p,root/'store')
            p.write_bytes(b'new');new=retain_source(p,root/'store')
            self.assertNotEqual(old,new);self.assertEqual(old.read_bytes(),b'old');self.assertEqual(new.read_bytes(),b'new')
    def test_corrupt_existing_object_fails_closed(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);p=root/'a.rs';p.write_bytes(b'expected');store=root/'store';store.mkdir()
            (store/(hashlib.sha256(b'expected').hexdigest()+'.rs')).write_bytes(b'corrupt')
            with self.assertRaises(ValueError):retain_source(p,store)
if __name__=='__main__':unittest.main()
