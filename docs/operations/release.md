# Change Integration and Release

Purpose: define repository hosting and release procedures. Scope: future remote
integration; M0 creates only a local repository.

Use short-lived branches and keep main buildable. Before integration run
[the complete gate](../../tools/check.sh), inspect the diff and lockfile, update
the accepted specification and changelog, and record evidence in task state.

When a remote is configured, enable a ruleset protecting main with required CPU,
docs, and smoke workflow checks; disable force pushes and deletion. Routine human
review is not required by this project's autonomous workflow. Remote protection
cannot be represented by local Git configuration and is not active in M0.

After a milestone's evidence passes, create an annotated tag such as
v0.1.0-foundation. Verify source archives, licenses, dependencies, reproducibility
metadata, and absence of private artifacts before an explicitly authorized push
or publication. No remote, release tag, or external publication is created by M0.
