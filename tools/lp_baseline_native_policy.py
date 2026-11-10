"""SPEC-0023 native-return observations, independent of mathematical acceptance."""
import math

from lp_baseline_common_v4 import require


NORMAL_TERMINATIONS = {
    'Optimal', 'PrimalFeasible', 'PrimalInfeasible', 'DualInfeasible',
    'UnboundedOrInfeasible', 'IterationLimit', 'TimeLimit',
}


def native_return_pass(observation):
    """No missing error field, unknown status or numerical error implies success."""
    return (observation.get('solution_returned') is True
            and type(observation.get('error_status')) is int
            and observation['error_status'] == 0
            and observation.get('error_message') == ''
            and observation.get('termination_reason') in NORMAL_TERMINATIONS)


def diagnostic(value):
    """Represent nonfinite diagnostics explicitly without forging numeric values."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, dict):
        return {str(k): diagnostic(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [diagnostic(x) for x in value]
    number = float(value)
    if not math.isfinite(number):
        return {'nonfinite': 'nan' if math.isnan(number) else ('+infinity' if number > 0 else '-infinity')}
    return number


def observe_solution(solution, canonical, parameters):
    require(solution is not None, 'cuOpt returned no Solution')
    status = solution.get_error_status()
    require(not isinstance(status, bool), 'boolean native error status')
    error_status = int(status)
    require(error_status == status, 'inexact native error status')
    message = solution.get_error_message()
    require(isinstance(message, str), 'missing native error message')
    termination = solution.get_termination_status()
    result = dict(schema_version=1, kind='lp-baseline-native-return', solver='cuopt',
        canonical=canonical, parameters=parameters, solution_returned=True,
        error_status=error_status, error_message=message,
        termination_code=int(termination), termination_reason=str(solution.get_termination_reason()),
        native_primal_objective=diagnostic(solution.get_primal_objective()),
        native_dual_objective=diagnostic(solution.get_dual_objective()),
        native_stats=diagnostic(solution.get_lp_stats()),
        native_solve_seconds=diagnostic(solution.get_solve_time()),
        solved_by=str(solution.get_solved_by()))
    result['native_return_pass'] = native_return_pass(result)
    return result


def comparison_pass(solver, transport_completed, certified, native=None):
    """A complete-latency pass still requires completed outer transport."""
    return bool(transport_completed and (
        native_return_pass(native or {}) if solver == 'cuopt' else certified))


def pending_screening(jobs, trials):
    """Reuse failed settled attempts as well as successful ones; never retry them."""
    return [j for j in jobs if j['phase'] == 'screening'
            and trials[j['id']]['status'] == 'unexecuted']


def quality_summary(certificate):
    validation = certificate['validation']
    result = dict(certified=certificate['accepted'],
        feasible=validation['feasible'] if validation else None,
        objective=validation['objective'] if validation else None,
        bound=certificate['bound'], gap_upper=certificate['gap_upper'],
        gap_closed=certificate['gap_closed'], refusal=certificate['refusal'])
    for group in ('variables', 'constraints'):
        count = 0
        maximum = 0.0
        ratio = 0.0
        worst = None
        if validation:
            for item in validation[group]:
                for side in ('lower', 'upper'):
                    value = item.get(side)
                    if not value:
                        continue
                    count += not value['satisfied']
                    maximum = max(maximum, value['violation'])
                    current = value['violation'] / value['allowance']
                    if current > ratio:
                        ratio = current
                        worst = dict(id=item.get('variable_id', item.get('constraint_id')),
                                     side=side, **value)
        result[group] = dict(violated_sides=count if validation else None,
            maximum_violation=maximum if validation else None,
            maximum_allowance_ratio=ratio if validation else None, worst=worst)
    return result
