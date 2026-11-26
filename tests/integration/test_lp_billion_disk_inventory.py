"""Native inventory must retain complete legacy semantics and fail closed."""
import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_billion_common as c
from lp_billion_test_support import native_inventory_fixture
class DiskInventoryContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.enterClassContext(native_inventory_fixture())

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
    def test_preflight_timeout_is_separate_from_runtime_sampling(self):
        with patch.object(c, 'native_inventory', return_value={'bytes': 7, 'files': 1}) as scan:
            self.assertEqual(c.preflight_disk_bytes(), 7)
            scan.assert_called_once_with(c.BASE, timeout_seconds=60)
            scan.reset_mock()
            self.assertEqual(c.disk_bytes(), 7)
            scan.assert_called_once_with(c.BASE)

    def test_inventory_timeout_is_bounded_and_has_no_automatic_retry(self):
        import subprocess
        for value in [0, -1, 61, float('inf'), float('nan'), True, '60']:
            with self.subTest(value=value), patch.object(c.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'bounded storage inventory timeout'):
                    c.native_inventory(c.BASE, timeout_seconds=value)
                run.assert_not_called()
        with patch.object(c, 'inventory_command', return_value=['inventory']), \
                patch.object(c.subprocess, 'run', side_effect=subprocess.TimeoutExpired('inventory', 60)) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                c.preflight_disk_bytes()
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.kwargs['timeout'], 60)
if __name__=='__main__':unittest.main()
