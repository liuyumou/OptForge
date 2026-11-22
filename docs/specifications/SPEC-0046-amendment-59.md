# SPEC-0046 amendment 59: proposed revised CPU phase transfer after retained failures

The candidate has not yet run on GPU. Retain all five CPU quality failures: v1
wrong offline Cargo cache (2400 CPU seconds), v2 misplaced guard (1920), v3 two
missing legacy test fields (1920), v4 ambiguous fixture integer type (1920), and
v5 lost_coordinator_heartbeat after 1.881 active seconds (560). All have empty
cleanup and no overrun; full charges are preserved. The compile issues are fixed.
The v5 heartbeat cause is not proven. Return to the previously successful one
Cargo worker; do not alter heartbeat, observation or ownership criteria.

The approved native phase now has only 16.517934412 CPU seconds, below a minimum
reservation. Proposed revised CPU caps are implementation8000/native22000/
admission52000/development140000/reporting97000/cleanup1000. This transfers 11000
unused development CPU seconds: 2000 implementation, 4000 native and 5000
reporting. GPU caps remain admission7000/development28000. Total allocation
remains 320000 CPU / 35000 GPU seconds, with every physical and certificate limit
unchanged. No additional total time, memory or storage is requested.

Development retains 29471.814412284 CPU seconds before the small cohort. The six
new billion solves reserve 24400 CPU / 6100 GPU seconds. Their audits reserve
21800 CPU seconds, plus reporting completion. Freeze only after the small cohort
settles and the full remaining solve/audit/storage reservations fit. Keep all six
families, unsupported capacities, failed attempts and uncertified endpoints.
No attempted scientific cell is retried.

If approved, add a second immutable transfer record preserving both previous
approvals, run fresh CPU operational acceptance, the unchanged five-minute idle
window and a fresh 120-second GPU operational reservation (previous complete
sixty-continuation exercise took 50.159 seconds). Native candidate acceptance
uses one build worker and a full 480-second reservation. Candidate bitwise packing,
sixty exact continuations and all four complete sanitizers still precede timing.
This proposal is not yet an applied cap change. No candidate measurement exists.
