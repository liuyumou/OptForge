# Change Integration and Release

Purpose: define repository hosting and release procedures. The project remote is
[liuyumou/OptForge](https://github.com/liuyumou/OptForge), configured as origin.
The main branch tracks origin/main after synchronization.

Use short-lived branches and keep main buildable. Before integration run
[the complete gate](../../tools/check.sh), inspect the diff and lockfile, update
the accepted specification and changelog, and record evidence in task state.

## Protected main

The active [Protect main ruleset](https://github.com/liuyumou/OptForge/rules/23515452)
was configured and verified on 2026-09-16. It applies to `refs/heads/main`:

- Changes require a pull request with all review conversations resolved.
- The branch must be up to date and pass the `cpu`, `docs` and `smoke` checks,
  originating from GitHub Actions (application ID 15368).
- Force pushes and branch deletion are blocked.
- No actors bypass the rules, including repository administrators.
- No approving review is mandatory, preserving the autonomous integration workflow.
  Existing approvals are dismissed when reviewable changes are pushed.

Use a branch and PR for completion documentation too. Do not disable protection
to finish an integration. Merge commits remain allowed to preserve archived
reference ancestry. GPU discovery is optional and is not a required status check.
The ruleset is remote configuration: verify its enforcement and effective rules
on main through GitHub after any administrative change.

After a milestone's evidence passes, create an annotated tag such as
v0.1.0-foundation. Verify source archives, licenses, dependencies, reproducibility
metadata, and absence of private artifacts before an explicitly authorized push
or publication. The initial GitHub synchronization publishes source history;
it does not create a release tag or configure hosting rulesets.
