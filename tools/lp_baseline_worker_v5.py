"""Same v4 worker and checker with explicit cuOpt error/status observations."""
import lp_baseline_worker_v4 as retained
import lp_baseline_adapters_v5 as adapters

retained.adapters = adapters

if __name__ == '__main__':
    raise SystemExit(retained.main())
