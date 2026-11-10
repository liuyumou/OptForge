"""CPU-only launch regressions; never invoke Cargo, a compiler or a device."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from lp_tensor_warp32_compile import child_environment, main


class Warp32CompilerLaunchTests(unittest.TestCase):
    def test_existing_interpreter_directory_remains_searchable(self):
        original = dict(PATH='/existing/python/bin:/usr/bin', KEPT='value')
        child = child_environment(original)
        self.assertEqual(child['PATH'], '/tmp/ai-optimizer-cargo/bin:/existing/python/bin:/usr/bin')
        self.assertEqual(child['KEPT'], 'value')
        self.assertEqual(original, dict(PATH='/existing/python/bin:/usr/bin', KEPT='value'))

    def test_compiler_uses_the_running_interpreter(self):
        with patch('lp_tensor_warp32_compile.subprocess.run') as run:
            main()
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[1].args[0][0], sys.executable)
        self.assertEqual(run.call_args_list[0].args[0][0], '/tmp/ai-optimizer-cargo/bin/cargo')

    def test_child_keeps_accepted_pool_limits(self):
        child = child_environment(dict(PATH=os.environ.get('PATH', ''), CARGO_BUILD_JOBS='4', OMP_NUM_THREADS='1'))
        self.assertEqual(child['CARGO_BUILD_JOBS'], '4')
        self.assertEqual(child['OMP_NUM_THREADS'], '1')
        self.assertEqual(child['RUSTUP_HOME'], '/tmp/ai-optimizer-rustup')

    def test_a_failed_first_command_cannot_start_compilation(self):
        import subprocess
        with patch('lp_tensor_warp32_compile.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'cargo')) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                main()
        self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
