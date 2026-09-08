# Change Integration and Release

Purpose: define repository hosting and release procedures. The project remote is
[liuyumou/OptForge](https://github.com/liuyumou/OptForge), configured as origin.
The main branch tracks origin/main after synchronization.

Use short-lived branches and keep main buildable. Before integration run
[the complete gate](../../tools/check.sh), inspect the diff and lockfile, update
the accepted specification and changelog, and record evidence in task state.

For hosted integration, enable a ruleset protecting main with required CPU,
docs, and smoke workflow checks; disable force pushes and deletion. Routine human
review is not required by this project's autonomous workflow. Remote protection
cannot be represented by local Git configuration and is a separate hosting step.

After a milestone's evidence passes, create an annotated tag such as
v0.1.0-foundation. Verify source archives, licenses, dependencies, reproducibility
metadata, and absence of private artifacts before an explicitly authorized push
or publication. The initial GitHub synchronization publishes source history;
it does not create a release tag or configure hosting rulesets.
