"""Explicit comparison and empirical capacity policy; no vendor status is a proof."""
import math
from lp_billion_common import require

GIB = 1 << 30
FAMILIES = ['irregular', 'wide', 'tall', 'coupled_blocks', 'ill_scaled', 'degenerate']
PROJECT_AUDITS = dict(zip(FAMILIES, [3500, 4500, 2800, 2000, 3500, 3500]))
VENDOR_AUDITS = dict(zip(FAMILIES, [500, 700, 500, 400, 500, 500]))


def timely(row, response, wall_seconds):
    """An accepted late endpoint remains useful evidence, not a timely solve."""
    if not row.get('timing_eligible') or not row.get('certified'):
        return False
    elapsed = response['elapsed_ns'] if row['lane'] == 'fp4x2' else response['solver_wall_ns']
    before = response.get('returned_before_deadline', True)
    return bool(before and elapsed <= wall_seconds * 1_000_000_000)


def forecast(model, rows, memory_mb):
    """All selected-configuration paths count, including failed/setup-only paths."""
    require(rows and all(r['family'] == model['family'] for r in rows), 'complete family capacity evidence')
    observed = [r for r in rows if r.get('response')]
    host = math.ceil(max((r['host_peak_bytes'] * model['nonzeros'] / r['nonzeros'] for r in observed), default=0) * 1.15) + 8 * GIB
    device = math.ceil(max((r['owned_device_peak_bytes'] * model['nonzeros'] / r['nonzeros'] for r in observed), default=0) * 1.15) + 4 * GIB
    vendor = max((r['vendor_mem_peak_mb'] * model['nonzeros'] / r['nonzeros'] for r in observed), default=0)
    arrays = 24 * model['nonzeros'] + 44 * model['columns'] + 24 * model['rows']
    reasons = []
    if not all(r['capacity_observed'] for r in rows):
        reasons.append('missing, interrupted or setup-only selected-configuration path')
    if host > 128 * GIB: reasons.append('empirical host forecast exceeds 128 GiB')
    if device > 80 * GIB: reasons.append('empirical device forecast exceeds 80 GiB')
    if arrays + 8 * GIB > 128 * GIB: reasons.append('adapter import arrays exceed host capacity')
    if vendor > memory_mb: reasons.append('reported vendor memory forecast exceeds soft setting')
    return dict(admitted=not reasons, reasons=reasons, host_gib=128, device_gib=80,
                host_bytes=128 * GIB, device_bytes=80 * GIB,
                empirical_host_peak_with_allowance=host, empirical_device_peak_with_allowance=device,
                forecast_vendor_mem_peak_mb=vendor, adapter_import_arrays_bytes=arrays,
                forecast_is_hard_enclosure=False, vendor_memory_limit_is_soft=True,
                source_cells=[r['id'] for r in rows])


def pair(project, vendor):
    require(project['family'] == vendor['family'], 'same original problem family')
    both = project.get('timely_strict_certificate', False) and vendor.get('timely_strict_certificate', False)
    return dict(family=project['family'], both_timely_strict_certified=both,
                copt_over_project_complete_ratio=vendor['complete_ns'] / project['complete_ns'] if both else None,
                project_status=project['status'], copt_status=vendor['status'])
