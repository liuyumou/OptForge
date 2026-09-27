# SPEC-0015: Compact Independently Verifiable LP Evidence

Status: accepted by the maintainer on 2026-09-27 before implementation
Scope: opt-in single-solve study output and lossless evidence conversion
Owner: experiment tooling and numerical backend
Introduced: GPUP-EVIDENCE
Last reviewed commit: bootstrap (GPUP-EVIDENCE; parent 04d899e)
Supersedes: none; extends SPEC-0013 through ADR-0027
Implementation: optimizer-experiment::lp_compact; optimizer-cli study output policy; tools/benchmark_lp_evidence.py and tools/report_lp_evidence.py
Tests: requirement mapping below

## Purpose

Restore assessable large-model evidence within the existing 32 MiB study output
cap. Preserve the original model, mathematical authority, solve record meaning,
legacy endpoints and defaults. This slice changes representation, not arithmetic.
Research-specific, batch/session, external COPT and ordinary solve formats are excluded.

## Terminology

A *legacy endpoint* is an ordinary `LpEndpoint` version 1–5. A *compact endpoint*
is a versioned envelope of that endpoint with its optional `record.validation`
omitted and a digest describing whether and how to reconstruct it. A *derived
artifact* is a conversion of an existing endpoint, never a new solve result.

## Requirements

1. Compact evidence MUST retain every legacy endpoint field except
   `record.validation`, including the original endpoint version and payload hash,
   original-model hash, candidate IDs/values, canonical dual/row IDs, settings,
   requested/executed identities, fallback, assessment and work observations.
2. The compact envelope MUST contain exactly `schema_version: 1`,
   `format: "lp-compact-v1"`, `endpoint`, and required nullable `validation_sha256`.
   The embedded record MUST omit `validation`, including explicit null.
3. A non-null validation digest MUST be lowercase SHA-256 of the compact serde
   JSON encoding of the complete original `ValidationReport`; null MUST mean the
   source record lacked validation. A digest without a candidate MUST be rejected.
4. Verification MUST check exact model identity, recompute validation using the
   original model, original candidate and recorded tolerances, check its digest,
   restore its presence, and invoke existing legacy endpoint verification. A
   digest or recorded assessment MUST NOT replace fresh host certification.
5. Parsing MUST reject missing/unknown/duplicate fields, positional objects,
   non-finite numbers, unsupported versions and inconsistent nested identities.
   Legacy endpoint shape rules MUST still apply to the embedded endpoint.
6. Serialization MUST use finite binary64 round-trip JSON without quantization or
   compression. Verified transcode round trips MUST retain legacy payload hashes
   and all numerical bits, including signed zero.
7. Only `lp-study solve` MUST accept `--evidence-format legacy|compact-v1`, with
   legacy as the unchanged default. Compact mode MUST write its endpoint and print
   the assessment JSON only, without producing the full solve-record stdout JSON.
   Ordinary `solve` MUST reject the study-only flag. Exit-code meanings stay unchanged.
8. `lp-study verify` MUST recognize both formats. `lp-study replay` MUST verify
   either source before execution and default to its format, with an explicit
   format override. Replay MUST retain existing executed-backend and code-identity rules.
9. `lp-study transcode` MUST require model, evidence, output and target format,
   verify before conversion, and perform no solve or device work. Failed/limited
   endpoints MUST remain failed/limited after conversion.
10. Replay/transcode MUST support the existing explicit study input bound on both
    model and evidence: 16 MiB by default, positive explicit limit at most 128 MiB.
    Profile flags MUST remain restricted to previously supported commands.
11. New compact/transcode destinations MUST be refused if already present before
    device work or conversion. Output MUST publish atomically without replacing an
    existing destination; failed writes MUST retain their partial file. Compact
    output MUST not change the supervisor's existing per-file cap.
12. The separately frozen gpup-evidence-v1 study MUST bind format choice into
    configuration/request identity, preserve historical artifacts and protocols,
    distinguish derived codec fixtures from live results, and retain every attempt.
13. CPU evidence MUST cover all four development extensions, report endpoint and
    stdout size, write and verification cost, and distinguish retained from synthetic
    full-witness fixtures. Compact full-witness fixtures MUST fit below 32 MiB.
14. Device format comparisons MUST preserve numerical bits under fixed work,
    including precision/adaptive records and replay. Separate timing runs MUST
    report fresh-process certified latency, failures and incomplete pairs; no
    verified limit or timeout MUST become certified success.
15. Resource admission MUST preserve the existing cumulative ceiling, original
    output binding, phase caps and ledger prefix, charge failed work, and serialize
    device jobs under the shared host lease. No new allowance is granted.

## Interfaces and state

`lp-compact-endpoint-v1.schema.json` describes the envelope. The embedded endpoint
uses its original version; its record follows the corresponding solve schema with
validation forbidden. The codec lives in optimizer-experiment, with no device
requirement. Core SolveRecord and legacy serializers remain unchanged.

`lp-study solve --evidence-format compact-v1 --lp-evidence PATH` selects compact
output. Verify auto-detects. Replay accepts an optional format, and transcode requires
one. Both formats can be transcode inputs; conversion independently verifies first.
Duplicate flags and incompatible command/flag combinations are argument errors.
The assessment printed by compact solve/transcode/replay has the same shape as
existing `lp-study verify` output. It is a summary, not another solve record.

A present validation digest requires reconstructing the report before checking the
unchanged legacy payload hash. An absent report is never silently inserted. Model
bytes are still external and hash-bound. Fresh verification never trusts a device.
Conversion receipts bind source and derivative bytes; they do not alter trial status.

## Errors, recovery and compatibility

Malformed input is refused before solving. Model/hash/validation disagreement is
invalid evidence. Existing numerical rejection, fallback, cancellation and work/time
limits retain their identity. A complete compact endpoint can independently verify
an unsuccessful result without qualifying for performance ranking.

Version 1–5 writers and all old protocols retain their behavior. Compact replay
normalizes verified evidence to the existing execution path. Atomic publication
uses a same-directory partial file and no-replace publication; a partial/destination
collision is refused rather than overwriting historical output.

## Security and resources

No new dependency, unsafe boundary, decompression or cached assessment. Bounds and
counter admission are unchanged. ADR-0027 freezes four build jobs/four CPU hours,
900 GPU seconds of ablations and 300 of repeatability inside existing authority.

## Acceptance mapping

- Requirements 1–6: versions 1–5 round trips; digest/presence and malformed JSON
  mutations; min/max, signed-zero, candidate absence, unsuccessful/fallback cases;
  preserved exact-rational certification regressions and legacy parsing.
- Requirements 7–11: study CLI defaults/flags, verify/replay/transcode, explicit
  input limits, preflight refusal, atomic publication and retained partial writes.
- Requirements 12–15: schema/protocol/clean-source budget tests, four-extension CPU
  measurements, regular device gate, fixed-work format/replay pairs, all 24 timing
  identities and independent report, ledger prefix and phase/cumulative receipts.
- Full pinned-native `bash tools/check.sh` is required before device admission.

## Acceptance evidence

The [bounded report](../benchmarks/lp-compact-evidence.md) records exact four-extension
round trips, size/write/verification measurements, full native acceptance, 55 regular
device tests, six fixed-work format pairs and six compact replays. All 24 fresh
attempts are retained: 15 independently verified endpoints, 12 certified timings.
New Rust tests live in optimizer-experiment/src/lp.rs and optimizer-cli/src/study_output.rs;
CLI, frozen-protocol, report and synthetic-budget tests are in
[tests/integration/test_lp_evidence.py](../../tests/integration/test_lp_evidence.py).
Failures, partial output, incomplete performance pairs and prior hardware gaps remain
explicit. See the [tutorial](../tutorials/lp-compact-evidence.md) for CLI compatibility.

## Open questions

Whether compact output improves certified latency or restores particular live
65536-row cells is an experimental outcome, not an acceptance assumption. Historical
racecheck and large-session gaps remain outside this slice.
