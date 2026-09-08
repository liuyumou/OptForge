# Documentation Rules

Purpose: keep project knowledge authoritative and navigable. Scope: all docs.

README gives purpose, status, supported platforms, quick start, and navigation.
Architecture describes ownership and constraints. Specifications define normative
behavior. ADRs record decisions. Tutorials give commands and expected output.
Operations covers build, leases, release, and recovery. Benchmarks define evidence.
The wiki links to these authorities and must not introduce behavior.

Normative documents identify subsystem owner, status, last reviewed commit,
implementation, and acceptance tests. The initial review marker is bootstrap,
meaning the first commit containing the file; subsequent reviews use exact commit
IDs. Specifications use numbered MUST/MUST NOT/SHOULD/MAY requirements, one per
statement, and explicitly describe errors, limits, units, tolerances, overflow,
determinism, compatibility, and unknowns. See the
[template](../specifications/TEMPLATE.md).

Accepted ADRs are immutable decisions; supersede them with a new record. Behavior
changes update documentation and CHANGELOG.md in the same change.

The [book builder](../../tools/build_docs.py) uses Python-Markdown, validates local
links and heading anchors, and writes HTML. External URLs are not fetched.
The two source planning documents are preserved inputs, excluded from recursive
book validation because they reference surveys not included in this workspace.
All maintained Markdown pages are checked. Public Rust APIs also build with rustdoc.
