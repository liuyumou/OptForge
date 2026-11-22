"""Aggregate completed capacity evidence; preserve the original failed report."""
from lp_billion_common import BASE, ROOT, put, load, ref, resolve, require, NS
from lp_billion_full_report import record
from lp_billion_copt_readiness import workspace_observed
from lp_billion_copt_fair_policy import FAMILIES, forecast, timely
from lp_billion_copt_fair_run import authorized, bindings, MEMORY_MB


def metadata(bound):
    result = dict(bound)
    result['capacity_policy'] = result.pop('capacity')
    result['original_runner'] = result.pop('source')
    result['source'] = ref(__file__)
    return result


def main():
    authorized()
    destination = BASE / 'copt-fair-capacity-v1.json'
    require(not destination.exists(), 'fresh capacity disposition; no prior output is replaced')
    selected = load(BASE / 'copt-diagnostic-results-v1.json')['selected_variant']
    paths = [BASE / 'copt-diagnostic-64m-v1/freeze.json'] + [BASE / f'copt-fair-capacity-{scale}-v1/freeze.json' for scale in ['64m', '256m', '512m']]
    rows = []
    for path in paths:
        require((path.parent / 'completed.json').exists(), 'complete capacity roster')
        for cell in load(path)['cells']:
            if cell['variant'] != selected: continue
            row = record(cell); response = load(resolve(row['response'])) if row.get('response') else None
            model = load(resolve(cell['model_result']))
            row['requested_solver_wall_ns'] = int(cell['wall_seconds'] * NS)
            if response:
                row['requested_wall_exceeded'] = response['solver_wall_ns'] > row['requested_solver_wall_ns']
                row['timely_strict_certificate'] = timely(row, response, cell['wall_seconds'])
            valid = bool(row.get('timing_eligible') and response and response['gpu_confirmed']
                         and row.get('sampled_peak_owned_device_bytes', 0) > 0
                         and workspace_observed(response, row.get('strict_endpoint_accepted', False)))
            if valid:
                require(row['sampled_aggregate_peak_rss_bytes'] - response['host_memory']['VmHWM'] <= 8 * (1 << 30), 'observed host coordination allowance')
            rows.append(dict(id=cell['id'], family=cell['family'], nonzeros=model['nonzeros'], capacity_observed=valid,
                             host_peak_bytes=response['host_memory']['VmHWM'] if response else 0,
                             owned_device_peak_bytes=row.get('sampled_peak_owned_device_bytes', 0),
                             vendor_mem_peak_mb=response['native']['MemPeak'] if response else 0,
                             response=row.get('response'), audit=row['audit'], settlement=row['settlement'], outcome=row))
    capacity = {family: forecast(load(BASE / f'models-1b-{family}-v1/result.json'), [r for r in rows if r['family'] == family], MEMORY_MB) for family in FAMILIES}
    put(destination, dict(status='all_capacity_outcomes_retained', selected_variant=selected, memory_mb=MEMORY_MB,
                          cells=rows, capacity=capacity, manifests=[ref(p) for p in paths], **metadata(bindings()),
                          retained_failed_aggregation=ref(BASE / 'resources/copt-fair-readiness-v1.settlement.json'),
                          correction=ref(ROOT / 'docs/specifications/SPEC-0046-amendment-82.md')))
    print({family: value['reasons'] for family, value in capacity.items()}, flush=True)


if __name__ == '__main__': main()
