"""Approved availability recovery using the unchanged worker admission helper."""
import os
from lp_tensor_warp32_compile import child_environment
import lp_tensor_warp32_common as common


def main():
    os.environ.update(child_environment(os.environ))
    common.JOURNAL = common.BASE / 'cpu-journal-availability-recovery-v9.json'
    from lp_tensor_warp32_run import main as run
    run()


if __name__ == '__main__':
    main()
