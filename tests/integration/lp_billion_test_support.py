"""Temporary native inventory for CPU tests without private experiment files."""
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

import lp_billion_common as common


@contextmanager
def native_inventory_fixture():
    with tempfile.TemporaryDirectory(prefix='lp-inventory-test-') as directory:
        root = Path(directory)
        source = common.ROOT / 'tools/lp_billion_disk_inventory.c'
        executable = root / 'inventory'
        subprocess.run(['cc', '-O2', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        str(source), '-o', str(executable)], check=True, timeout=60,
                       capture_output=True, text=True)
        binding = root / 'binding.json'
        binding.write_text(json.dumps(dict(status='retained_for_cpu_bootstrap',
            executable=dict(path=executable.name, sha256=common.digest(executable)),
            source=dict(path=str(source.relative_to(common.ROOT)), sha256=common.digest(source)))))
        with patch.multiple(common, INVENTORY_ROOT=root, INVENTORY_BINDING=binding,
                            INVENTORY_BINDING_SHA=common.digest(binding)):
            yield
