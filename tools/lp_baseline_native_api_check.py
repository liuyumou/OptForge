"""Inspect the pinned cuOpt Solution ABI using a synthetic CPU-only object."""
from cuopt.linear_programming.solution.solution import Solution
from cuopt.linear_programming.solver.solver_wrapper import LPTerminationStatus, ProblemCategory
from lp_baseline_native_policy import observe_solution, native_return_pass

solution = Solution(problem_category=ProblemCategory.LP, vars={},
                    termination_status=LPTerminationStatus.Optimal.value,
                    error_status=0, error_message='', primal_objective=4.25,
                    dual_objective=3.75, primal_residual=0., dual_residual=0., gap=.5,
                    nb_iterations=12, solve_time=.01)
observation = observe_solution(solution, {'path':'synthetic-canonical','sha256':'0'*64}, {})
assert observation['termination_code'] == 1
assert observation['termination_reason'] == 'Optimal'
assert native_return_pass(observation)
assert observation['native_stats']['gap'] == .5
solution.error_status = 1
assert not native_return_pass(observe_solution(solution, {}, {}))
print('Pinned cuOpt Solution API observation passed; synthetic CPU-only object, no Solve or device call.')
