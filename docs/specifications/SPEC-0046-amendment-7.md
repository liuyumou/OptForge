# SPEC-0046 amendment 7: unlisted GPU memory and timing exclusion

Read-only NVML inspection found approximately 10 GiB of allocated memory with no
listed compute, graphics or MPS process. The installed NVML header confirms the
process structure ABI is correct. Driver-reserved memory explains only about
637 MiB; the original idle observations used 804978688 bytes including the driver.
The cause and owner of the extra memory remain unknown. Do not reset the device,
signal unrelated processes, or treat zero utilization alone as permission to run.

Prospectively require total used memory minus attributed process memory to be at
most 2 GiB, including driver memory, in every idle and supervised GPU sample.
Bracket the memory query with process inventories and take their per-process
maximum to tolerate context transitions between sequential NVML calls. Keep the
one-second supervisor, all 100 ms advisories, resource ceilings and pinned lease.
The allowance is fixed; it cannot be rebased to the current unexplained usage.

An additive audit binds every prior GPU reservation and capacity trace. Both
512 M image-v2 observations have sustained unattributed memory above this bound;
their timings are ineligible. Preserve responses, original successful resource
receipts, complete charges and independent numerical checking. Do not retry the
cells or infer their performance. Earlier observations that stayed below the bound
retain their existing status; this retrospective audit does not invent missing
telemetry or prove historical absence of smaller unlisted work.

Operational readmission v6 supersedes the never-started v5 GPU admission. Fresh
CPU resource tests precede the old image-v2 GPU continuation suite, which may run
only after the stricter idle checks pass. New numerical preparation admission is
still separate. CPU admission, cleanup and reporting can continue while the GPU
is unavailable. No total allocation, numerical criterion or publication changes.
