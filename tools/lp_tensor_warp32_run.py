"""One serialized, source-frozen ADR-0045 worker phase; never retries a cell."""
import shutil
import sys
from lp_protocol import ROOT, read_json, write_json
from lp_tensor_warp32_common import BASE, protocol, ledger_for
from benchmark_lp_tensor_warp32 import freeze, jobs, run_trial
from lp_tensor_warp32_accept import run_acceptance
from lp_tensor_warp32_screen import forecast, resource_forecast


def main():
    value = protocol()
    directory, identity = freeze(value)
    stage = 'acceptance'
    try:
        run_acceptance(value, directory, identity)
        stage = 'profiles'
        with ledger_for(value) as ledger:
            for job in jobs(value):
                if job['kind'] == 'profile':
                    run_trial(value, job, directory, ledger, identity)
            shutil.copy2(ledger.path, directory / 'ledger.jsonl')
        stage = 'forecast'
        screen = forecast(value, directory, identity)
        fit = resource_forecast(value, directory, identity) if screen['passed'] else dict(passed=False, reason='gain_forecast_refusal')
        if screen['passed'] and fit['passed']:
            stage = 'timings'
            with ledger_for(value) as ledger:
                for job in jobs(value):
                    if job['kind'] == 'timing':
                        run_trial(value, job, directory, ledger, identity)
                shutil.copy2(ledger.path, directory / 'ledger.jsonl')
        else:
            write_json(directory / 'timing-refusal.json', dict(reason='frozen_gain_or_resource_forecast_refusal', gain=screen, resource=fit))
            print('Frozen forecast refuses primary timings; no retry or extra cells', flush=True)
        stage = 'report'
        from report_lp_tensor_warp32 import report
        result = report()
        write_json(BASE / 'report-v1.json', result)
        print(dict(status=result['status'], certified_timings=result['certified_timings'],
                   task_gpu_ns=result['task_gpu_ns'], certified_latency_gain=result['certified_latency_gain']), flush=True)
    except BaseException as error:
        write_json(BASE / 'execution-stop-v1.json', dict(stage=stage, reason=str(error), status='incomplete'))
        raise


if __name__ == '__main__':
    main()
