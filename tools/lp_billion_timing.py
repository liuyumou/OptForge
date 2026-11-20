"""Exact exclusive cost ledgers; nested metrics are deliberately not summed twice."""
from lp_billion_common import require

PHASES = ('preparation_engine preparation_operator preparation_packing preparation_control '
          'device_setup host_bookkeeping checkpoint device_advance endpoint_download '
          'device_accounting original_model_control recovery endpoint_unscale strict_certificate '
          'witness_output restart_weight_control state_upload device_teardown response_assembly '
          'certificate_reuse').split()


def nonnegative(value):
    return type(value) is int and value >= 0


def validate_profile(response):
    p = response['solver_profile']
    require(p['schema_version'] == 1 and p['clock'] == 'monotonic_host_wall', 'profile clock/schema')
    require(p['timer_overhead_included'] is True and p['kernel_active_time'] is False, 'profile timing semantics')
    for key in ['exclusive_ns', 'phase_entries']:
        require(set(p[key]) == set(PHASES) and all(nonnegative(v) for v in p[key].values()), 'profile phase domain')
    require(nonnegative(p['total_ns']) and sum(p['exclusive_ns'].values()) == p['total_ns'], 'profile exact coverage')
    require(nonnegative(response['elapsed_ns']) and response['elapsed_ns'] >= p['total_ns'], 'profile solver interval')
    return p


def process_ledger(response, measured, final_check_ns=0):
    """Fresh process + persistence + independent final checking, in disjoint intervals."""
    p = validate_profile(response)
    for value in [response['input_ns'], measured['process_ns'], measured['response_transport_ns'],
                  measured['fresh_process_ns'], final_check_ns]:
        require(nonnegative(value), 'process timing domain')
    require(measured['process_ns'] + measured['response_transport_ns'] == measured['fresh_process_ns'], 'process transport coverage')
    residual = measured['process_ns'] - response['input_ns'] - response['elapsed_ns']
    require(residual >= 0, 'process interval smaller than solver/input')
    costs = dict(p['exclusive_ns'], input_hash_validation=response['input_ns'],
                 solver_profile_finalization=response['elapsed_ns'] - p['total_ns'],
                 process_startup_serialization_cleanup=residual,
                 response_transport=measured['response_transport_ns'], independent_final_check=final_check_ns)
    total = measured['fresh_process_ns'] + final_check_ns
    require(sum(costs.values()) == total, 'complete cost coverage')
    return dict(schema_version=1, total_ns=total, exclusive_ns=costs,
                nested_preparation_ns=response.get('preparation_detail_ns'),
                nested_gpu_preparation=response.get('gpu_preparation'),
                kernel_active_time=False, offline_intermediate_audit_included=False)
