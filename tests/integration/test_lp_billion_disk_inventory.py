"""Native inventory must retain complete legacy semantics and fail closed."""
import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_billion_common as c
class DiskInventoryContracts(unittest.TestCase):
    def test_exact_nested_files_hardlinks_symlinks_and_fifo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'empty').mkdir();(root/'nested').mkdir()
            for i,name in enumerate(['normal','space name','line\nbreak','unicode-λ']):
                (root/'nested'/name).write_bytes(bytes([i])*(i*17+1))
            os.link(root/'nested/normal',root/'hardlink');os.mkfifo(root/'fifo')
            (root/'symlink').symlink_to(root/'nested/normal');(root/'dirlink').symlink_to(root/'nested',target_is_directory=True);(root/'broken').symlink_to(root/'missing')
            result=c.native_inventory(root)
            self.assertEqual(result['bytes'],c.legacy_disk_bytes(root));self.assertEqual(result['files'],5)
    def test_empty_missing_and_sparse_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.assertEqual(c.native_inventory(root),dict(bytes=0,files=0))
            self.assertEqual(c.native_inventory(root/'missing'),dict(bytes=0,files=0))
            with (root/'sparse').open('wb') as stream:stream.truncate(1<<20)
            self.assertEqual(c.native_inventory(root)['bytes'],1<<20)
    def test_wrong_root_type_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'file').write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'inventory failed'):c.native_inventory(root/'file')
    def test_changed_binding_refuses_before_execution(self):
        with patch.object(c,'digest',return_value='altered'),patch.object(c.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'binding integrity'):c.native_inventory(c.BASE)
            run.assert_not_called()
if __name__=='__main__':unittest.main()
